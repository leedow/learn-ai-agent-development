from funasr import AutoModel
import time
import soundfile
import os
import torch

chunk_size = [0, 10, 5] #[0, 10, 5] 600ms, [0, 8, 4] 480ms
encoder_chunk_look_back = 4 #number of chunks to lookback for encoder self-attention
decoder_chunk_look_back = 1 #number of encoder chunks to lookback for decoder cross-attention

# 检测并配置 GPU
device = "cuda:0" if torch.cuda.is_available() else "cpu"
if torch.cuda.is_available():
    print(f"使用 GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU 显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
else:
    print("未检测到 GPU，将使用 CPU")

# 记录模型加载时间
print("\n正在加载模型...")
model_load_start = time.perf_counter()
model = AutoModel(model="paraformer-zh-streaming", device=device)


 
model_load_end = time.perf_counter()
model_load_time = model_load_end - model_load_start
print(f"模型加载完成！耗时: {model_load_time:.2f} 秒 ({model_load_time*1000:.2f} 毫秒)")

wav_file = os.path.join(model.model_path, "example/asr_example.wav")
speech, sample_rate = soundfile.read("/home/leedow/下载/asr_example_zh.wav")
chunk_stride = chunk_size[1] * 960 # 600ms

cache = {}
total_chunk_num = int(len((speech)-1)/chunk_stride+1)

print(f"\n音频总长度: {len(speech)/sample_rate:.2f} 秒")
print(f"采样率: {sample_rate} Hz")
print(f"Chunk 大小: {chunk_stride/sample_rate*1000:.0f} ms")
print(f"总 Chunk 数: {total_chunk_num}")
print("\n开始推理...")
print("="*60)

# 记录推理时间
inference_times = []
total_inference_start = time.perf_counter()

for i in range(total_chunk_num):
    speech_chunk = speech[i*chunk_stride:(i+1)*chunk_stride]
    is_final = i == total_chunk_num - 1
    
    # 记录每个 chunk 的推理时间
    chunk_start = time.perf_counter()
    res = model.generate(input=speech_chunk, cache=cache, use_itn=True, is_final=is_final, chunk_size=chunk_size, encoder_chunk_look_back=encoder_chunk_look_back, decoder_chunk_look_back=decoder_chunk_look_back)
    chunk_end = time.perf_counter()
    chunk_time = chunk_end - chunk_start
    inference_times.append(chunk_time)
    
    print(f"Chunk {i+1}/{total_chunk_num}: {chunk_time*1000:.2f} ms - {res}")

total_inference_end = time.perf_counter()
total_inference_time = total_inference_end - total_inference_start

# 统计信息
print("\n" + "="*60)
print("推理性能统计:")
print("="*60)
print(f"推理设备: {device}")
print(f"模型加载时间: {model_load_time:.2f} 秒 ({model_load_time*1000:.2f} 毫秒)")

if inference_times:
    # 第一次推理（包含预热）
    first_inference_time = inference_times[0]
    
    # 后续推理（排除第一次）
    subsequent_times = inference_times[1:] if len(inference_times) > 1 else []
    
    # 总推理时间
    print(f"\n总推理时间: {total_inference_time:.2f} 秒 ({total_inference_time*1000:.2f} 毫秒)")
    print(f"处理的 Chunk 数: {len(inference_times)}")
    
    # 第一次推理（含预热）
    print(f"\n第一次推理（含预热）:")
    print(f"  耗时: {first_inference_time:.2f} 秒 ({first_inference_time*1000:.2f} 毫秒)")
    
    # 后续推理统计
    if subsequent_times:
        avg_time = sum(subsequent_times) / len(subsequent_times)
        min_time = min(subsequent_times)
        max_time = max(subsequent_times)
        
        # 计算预热时间
        warmup_time = first_inference_time - avg_time if first_inference_time > avg_time else 0
        
        print(f"\n后续推理统计（{len(subsequent_times)} 次，不含预热）:")
        print(f"  平均耗时: {avg_time:.2f} 秒 ({avg_time*1000:.2f} 毫秒)")
        print(f"  最小耗时: {min_time:.2f} 秒 ({min_time*1000:.2f} 毫秒)")
        print(f"  最大耗时: {max_time:.2f} 秒 ({max_time*1000:.2f} 毫秒)")
        
        if warmup_time > 0:
            print(f"  预热时间: {warmup_time:.2f} 秒 ({warmup_time*1000:.2f} 毫秒)")
            warmup_ratio = (warmup_time / first_inference_time) * 100
            print(f"  预热时间占比: {warmup_ratio:.1f}%")
        
        # 吞吐量（每秒处理的 chunk 数）
        throughput = 1.0 / avg_time if avg_time > 0 else 0
        print(f"  吞吐量: {throughput:.2f} chunks/秒")
    
    # 所有推理的统计
    all_avg_time = sum(inference_times) / len(inference_times)
    all_min_time = min(inference_times)
    all_max_time = max(inference_times)
    
    print(f"\n所有推理统计（{len(inference_times)} 次）:")
    print(f"  平均耗时: {all_avg_time:.2f} 秒 ({all_avg_time*1000:.2f} 毫秒)")
    print(f"  最小耗时: {all_min_time:.2f} 秒 ({all_min_time*1000:.2f} 毫秒)")
    print(f"  最大耗时: {all_max_time:.2f} 秒 ({all_max_time*1000:.2f} 毫秒)")
    
    # 实时因子（Real-time Factor）
    audio_duration = len(speech) / sample_rate
    rtf = total_inference_time / audio_duration if audio_duration > 0 else 0
    print(f"\n实时因子 (RTF): {rtf:.3f}")
    if rtf < 1.0:
        print(f"  推理速度: {1.0/rtf:.2f}x 实时速度")
    else:
        print(f"  推理速度: {rtf:.2f}x 音频时长")

print("="*60)