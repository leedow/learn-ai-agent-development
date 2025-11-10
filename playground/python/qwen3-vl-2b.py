from modelscope import Qwen3VLForConditionalGeneration, AutoProcessor
import torch
import time
import os
import sys
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Check GPU availability
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"使用设备: {device}")
if torch.cuda.is_available():
    print(f"GPU 名称: {torch.cuda.get_device_name(0)}")
    print(f"GPU 内存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
else:
    print("警告: 未检测到GPU，将使用CPU运行")

# Reset memory stats before loading
if torch.cuda.is_available():
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.empty_cache()

# Load the model on GPU wi
# th bfloat16 for better performance
print("\n正在加载模型...")
model_load_start_mem = torch.cuda.memory_allocated() / 1024**3 if torch.cuda.is_available() else 0

model = Qwen3VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen3-VL-2B-Instruct",
    torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)
print(f"模型已加载到: {model.device}")

# Record memory after model loading
if torch.cuda.is_available():
    model_load_end_mem = torch.cuda.memory_allocated() / 1024**3
    print(f"模型加载后显存: {model_load_end_mem:.2f} GB")

# We recommend enabling flash_attention_2 for better acceleration and memory saving, especially in multi-image and video scenarios.
# model = Qwen3VLForConditionalGeneration.from_pretrained(
#     "Qwen/Qwen3-VL-2B-Instruct",
#     dtype=torch.bfloat16,
#     attn_implementation="flash_attention_2",
#     device_map="auto",
# )

processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-2B-Instruct")

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image",
                "image": "http://localhost/123.jpeg",
            },
            {"type": "text", "text": "这张图片中你看到了什么"},
        ],
    }
]

# Preparation for inference
print("\n正在处理输入（包括图像下载和预处理）...")
prep_start_time = time.perf_counter()

inputs = processor.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_dict=True,
    return_tensors="pt"
)
inputs = inputs.to(model.device)

prep_end_time = time.perf_counter()
prep_time = prep_end_time - prep_start_time
print(f"输入预处理耗时: {prep_time:.2f} 秒 ({prep_time*1000:.2f} 毫秒)")

# Inference: Generation of the output
print("\n开始生成...")
print("="*50)
print("生成结果 (流式输出):")
print("="*50)

# Create a streamer for streaming output and capturing first token latency
class StreamingTextStreamer:
    def __init__(self, tokenizer, skip_prompt=False, skip_special_tokens=True):
        self.tokenizer = tokenizer
        self.skip_prompt = skip_prompt
        self.skip_special_tokens = skip_special_tokens
        self.first_token_time = None
        self.previous_token_time = None
        self.token_count = 0
        self.generated_tokens = []
        self.current_text = ""
        self.token_intervals = []  # 存储每个token的时间间隔
        
    def put(self, value):
        """Called when a new token is generated - 这个方法在每个token生成时立即被调用"""
        current_time = time.perf_counter()
        
        # 计算与上一个token的时间差
        if self.previous_token_time is not None:
            interval = current_time - self.previous_token_time
            self.token_intervals.append(interval)
            interval_ms = interval * 1000
            print(f"[间隔: {interval_ms:.2f}ms]", end='', flush=True)
        elif self.token_count == 0:
            self.first_token_time = current_time
            print(f"[首个Token]", end='', flush=True)
        
        self.previous_token_time = current_time

        # Store the token
        if isinstance(value, torch.Tensor):
            token_ids = value.cpu().tolist()
        else:
            token_ids = value
            
        # Handle both single token and batch of tokens
        if isinstance(token_ids[0], list):
            token_ids = token_ids[0]
        
        self.generated_tokens.extend(token_ids)
        self.token_count += 1
        
        # Decode and print the new text
        try:
            new_text = self.tokenizer.decode(
                self.generated_tokens,
                skip_special_tokens=self.skip_special_tokens
            )
            
            # Only print the new part (incremental text)
            if len(new_text) > len(self.current_text):
                incremental_text = new_text[len(self.current_text):]
                print(incremental_text, end='', flush=True)
                self.current_text = new_text
        except Exception as e:
            # If decoding fails, just continue
            pass
        
    def end(self):
        """Called when generation is complete"""
        print()  # New line after streaming
        pass

# Reset peak memory stats before generation
if torch.cuda.is_available():
    torch.cuda.reset_peak_memory_stats()

# Record memory before generation
gen_start_mem = 0
gen_start_ram = 0
if torch.cuda.is_available():
    gen_start_mem = torch.cuda.memory_allocated() / 1024**3

if PSUTIL_AVAILABLE:
    process = psutil.Process(os.getpid())
    gen_start_ram = process.memory_info().rss / 1024**3

# Create streaming text streamer
streamer = StreamingTextStreamer(
    tokenizer=processor.tokenizer,
    skip_prompt=True,
    skip_special_tokens=True
)

# Start timing from RIGHT BEFORE model.generate() call
# This is the TRUE start time for first token latency
true_start_time = time.perf_counter()

# Generate with streamer for real-time output
generated_ids = model.generate(
    **inputs,
    max_new_tokens=128,
    streamer=streamer,
    do_sample=False,
    use_cache=True,
)

end_time = time.perf_counter()
generation_time = end_time - true_start_time

# Record peak memory after generation
gen_end_mem = 0
peak_gpu_mem = 0
peak_gpu_reserved = 0
gen_end_ram = 0

if torch.cuda.is_available():
    gen_end_mem = torch.cuda.memory_allocated() / 1024**3
    peak_gpu_mem = torch.cuda.max_memory_allocated() / 1024**3
    peak_gpu_reserved = torch.cuda.max_memory_reserved() / 1024**3

if PSUTIL_AVAILABLE:
    gen_end_ram = process.memory_info().rss / 1024**3

# Calculate first token latency (TRUE TTFT - from model.generate() call to first token)
if streamer.first_token_time:
    first_token_latency = streamer.first_token_time - true_start_time
    # Total time including preprocessing
    total_time_with_prep = first_token_latency + prep_time
else:
    first_token_latency = None
    total_time_with_prep = None

# Get the final generated text
generated_ids_trimmed = [
    out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
]
output_text = processor.batch_decode(
    generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
)

# Calculate tokens
num_tokens = len(generated_ids_trimmed[0]) if generated_ids_trimmed else 0
tokens_per_second = num_tokens / generation_time if generation_time > 0 else 0

print("\n" + "="*50)
print("性能统计:")
print("-" * 50)
print(f"输入预处理时间: {prep_time:.2f} 秒 ({prep_time*1000:.2f} 毫秒)")
if first_token_latency is not None:
    print(f"首 Token 延迟 (TTFT - 仅生成): {first_token_latency*1000:.2f} 毫秒 ({first_token_latency:.4f} 秒)")
    if total_time_with_prep is not None:
        print(f"首 Token 总延迟 (含预处理): {total_time_with_prep:.2f} 秒 ({total_time_with_prep*1000:.2f} 毫秒)")
print(f"总生成耗时: {generation_time:.2f} 秒 ({generation_time*1000:.2f} 毫秒)")
print(f"完整流程总耗时: {(generation_time + prep_time):.2f} 秒 ({(generation_time + prep_time)*1000:.2f} 毫秒)")
print(f"生成 Token 数: {num_tokens}")
print(f"生成速度: {tokens_per_second:.2f} tokens/秒")
if first_token_latency is not None and generation_time > first_token_latency:
    subsequent_time = generation_time - first_token_latency
    subsequent_tokens = num_tokens - 1
    if subsequent_tokens > 0:
        subsequent_speed = subsequent_tokens / subsequent_time
        print(f"后续 Token 速度: {subsequent_speed:.2f} tokens/秒")

# Token间隔统计
if streamer.token_intervals:
    intervals_ms = [interval * 1000 for interval in streamer.token_intervals]
    avg_interval = sum(intervals_ms) / len(intervals_ms)
    min_interval = min(intervals_ms)
    max_interval = max(intervals_ms)
    print(f"\nToken 间隔统计:")
    print(f"  平均间隔: {avg_interval:.2f} 毫秒")
    print(f"  最小间隔: {min_interval:.2f} 毫秒")
    print(f"  最大间隔: {max_interval:.2f} 毫秒")
    print(f"  总间隔数: {len(intervals_ms)}")
print("\n内存统计:")
print("-" * 50)
if torch.cuda.is_available():
    total_gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"GPU 显存:")
    print(f"  当前分配: {gen_end_mem:.2f} GB")
    print(f"  峰值分配: {peak_gpu_mem:.2f} GB")
    print(f"  峰值预留: {peak_gpu_reserved:.2f} GB")
    print(f"  总显存: {total_gpu_mem:.2f} GB")
    print(f"  峰值使用率: {(peak_gpu_mem/total_gpu_mem)*100:.1f}%")
    if gen_start_mem > 0:
        mem_increase = gen_end_mem - gen_start_mem
        print(f"  生成期间增加: {mem_increase:.2f} GB")
if PSUTIL_AVAILABLE:
    print(f"\n系统内存 (RAM):")
    print(f"  当前使用: {gen_end_ram:.2f} GB")
    if gen_start_ram > 0:
        ram_increase = gen_end_ram - gen_start_ram
        print(f"  生成期间增加: {ram_increase:.2f} GB")
else:
    print("\n提示: 安装 psutil 可查看系统内存统计 (pip install psutil)")
print("="*50)