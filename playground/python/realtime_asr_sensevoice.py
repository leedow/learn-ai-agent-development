"""
实时语音识别 - 使用 iic/SenseVoiceSmall 模型
通过 ModelScope 加载模型，实时采集音频并转换为文字
"""

import sys

# 检查并安装必要的依赖
def check_dependencies():
    """检查必要的依赖包"""
    missing_deps = []
    
    # 检查基础依赖
    try:
        import torch
    except ImportError:
        missing_deps.append("torch")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import addict
    except ImportError:
        missing_deps.append("addict")
    
    try:
        import modelscope
    except ImportError:
        missing_deps.append("modelscope")
    
    if missing_deps:
        print("错误: 缺少以下依赖包:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\n请运行以下命令安装缺失的依赖:")
        print(f"  pip install {' '.join(missing_deps)}")
        sys.exit(1)

# 先检查依赖
check_dependencies()

import torch
import time
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

# 延迟导入 modelscope，避免版本兼容性问题
def load_asr_pipeline():
    """加载 ASR pipeline，处理音频依赖问题"""
    try:
        inference_pipeline = pipeline(
            task=Tasks.auto_speech_recognition,
            model='iic/SenseVoiceSmall',
            model_revision="master",
            device="cuda:0" if torch.cuda.is_available() else "cpu",
        )
        return inference_pipeline
    except ImportError as e:
        error_msg = str(e)
        if "audio" in error_msg.lower() or "funasr" in error_msg.lower():
            print("\n" + "="*60)
            print("错误: 缺少音频相关依赖")
            print("="*60)
            print("SenseVoice 模型需要安装 modelscope 的音频扩展。")
            print(f"\n详细错误: {error_msg}")
            print("\n解决方案:")
            print("请运行以下命令安装音频相关依赖:")
            print("  pip install 'modelscope[audio]' -f https://modelscope.oss-cn-beijing.aliyuncs.com/releases/repo.html")
            print("\n或者使用国内镜像（更快）:")
            print("  pip install 'modelscope[audio]' -f https://modelscope.oss-cn-beijing.aliyuncs.com/releases/repo.html -i https://pypi.tuna.tsinghua.edu.cn/simple")
            print("\n注意: 在 zsh 中需要使用引号包裹包名，避免方括号被解释为通配符")
            print("="*60)
        else:
            print(f"\n错误: 无法加载模型: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: 加载模型时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# 显存统计函数
def get_gpu_memory_info():
    """获取GPU显存信息"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3  # GB
        reserved = torch.cuda.memory_reserved() / 1024**3  # GB
        max_allocated = torch.cuda.max_memory_allocated() / 1024**3  # GB
        max_reserved = torch.cuda.max_memory_reserved() / 1024**3  # GB
        total = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
        return {
            'allocated': allocated,
            'reserved': reserved,
            'max_allocated': max_allocated,
            'max_reserved': max_reserved,
            'total': total
        }
    return None

def print_memory_info(label, memory_info):
    """打印显存信息"""
    if memory_info:
        print(f"{label}:")
        print(f"  当前分配: {memory_info['allocated']:.2f} GB")
        print(f"  当前预留: {memory_info['reserved']:.2f} GB")
        print(f"  峰值分配: {memory_info['max_allocated']:.2f} GB")
        print(f"  峰值预留: {memory_info['max_reserved']:.2f} GB")
        print(f"  总显存: {memory_info['total']:.2f} GB")
        usage_ratio = (memory_info['max_allocated'] / memory_info['total']) * 100
        print(f"  峰值使用率: {usage_ratio:.1f}%")

# 初始化显存统计
if torch.cuda.is_available():
    torch.cuda.reset_peak_memory_stats()
    print(f"\nGPU 设备: {torch.cuda.get_device_name(0)}")
    print(f"总显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    initial_memory = get_gpu_memory_info()
    print_memory_info("初始显存状态", initial_memory)
else:
    print("\n警告: 未检测到GPU，将使用CPU运行（无法统计显存）")
    initial_memory = None

# 加载模型
print("\n正在加载 ASR 模型 (iic/SenseVoiceSmall)...")
print("这可能需要一些时间，请耐心等待...")
model_load_start = time.perf_counter()
inference_pipeline = load_asr_pipeline()
model_load_end = time.perf_counter()
model_load_time = model_load_end - model_load_start

# 模型加载后的显存
if torch.cuda.is_available():
    after_load_memory = get_gpu_memory_info()
    load_memory_increase = after_load_memory['allocated'] - initial_memory['allocated'] if initial_memory else 0
    print(f"\n模型加载完成！耗时: {model_load_time:.2f} 秒 ({model_load_time*1000:.2f} 毫秒)")
    print_memory_info("模型加载后显存状态", after_load_memory)
    print(f"模型加载显存增加: {load_memory_increase:.2f} GB")
else:
    print(f"模型加载完成！耗时: {model_load_time:.2f} 秒 ({model_load_time*1000:.2f} 毫秒)")

# 测试识别（使用示例音频）
print("\n" + "="*60)
print("开始测试识别（使用示例音频）...")
print("="*60)

# 预热时间说明
print("\n" + "-"*60)
print("关于预热时间（Warm-up Time）:")
print("-"*60)
print("预热时间是指第一次推理时，模型需要执行的额外初始化操作，包括:")
print("  • GPU内存分配和初始化")
print("  • CUDA kernel编译（JIT编译）")
print("  • 运行时缓存初始化")
print("  • 模型权重加载到GPU（如果延迟加载）")
print("  • 其他一次性初始化操作")
print("因此第一次推理通常比后续推理慢，这就是'预热'的概念。")
print("-"*60)

# 第一次推理（包含预热时间）
print("\n第一次推理（包含预热时间）...")
if torch.cuda.is_available():
    torch.cuda.reset_peak_memory_stats()  # 重置峰值统计，只统计推理期间的显存
    before_inference_memory = get_gpu_memory_info()

inference_start = time.perf_counter()
rec_result = inference_pipeline('https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/test_audio/asr_example_zh.wav')
inference_end = time.perf_counter()
first_inference_time = inference_end - inference_start

if torch.cuda.is_available():
    after_inference_memory = get_gpu_memory_info()
    inference_memory_increase = after_inference_memory['max_allocated'] - before_inference_memory['allocated']

print(f"识别结果: {rec_result}")
print(f"第一次推理耗时（含预热）: {first_inference_time:.2f} 秒 ({first_inference_time*1000:.2f} 毫秒)")
if torch.cuda.is_available():
    print(f"第一次推理显存峰值: {after_inference_memory['max_allocated']:.2f} GB (增加 {inference_memory_increase:.2f} GB)")

# 多次推理计算平均时间（排除第一次预热，这些是真正的推理时间）
print("\n进行多次推理以计算平均耗时（排除第一次预热）...")
print("这些推理时间代表模型在实际使用中的真实性能。")
num_runs = 5
inference_times = []
inference_memory_peaks = []  # 记录每次推理的显存峰值

for i in range(num_runs):
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        before_memory = get_gpu_memory_info()
    
    inference_start = time.perf_counter()
    rec_result = inference_pipeline('https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/test_audio/asr_example_zh.wav')
    inference_end = time.perf_counter()
    inference_time = inference_end - inference_start
    inference_times.append(inference_time)
    
    if torch.cuda.is_available():
        after_memory = get_gpu_memory_info()
        peak_memory = after_memory['max_allocated']
        inference_memory_peaks.append(peak_memory)
        print(f"  第 {i+1} 次推理: {inference_time*1000:.2f} 毫秒, 显存峰值: {peak_memory:.2f} GB")
    else:
        print(f"  第 {i+1} 次推理: {inference_time*1000:.2f} 毫秒")

# 统计信息
if inference_times:
    avg_time = sum(inference_times) / len(inference_times)
    min_time = min(inference_times)
    max_time = max(inference_times)
    
    # 计算预热时间（第一次推理 - 平均推理时间）
    warmup_time = first_inference_time - avg_time if first_inference_time > avg_time else 0
    
    print("\n" + "="*60)
    print("推理性能统计:")
    print("="*60)
    print(f"模型加载时间: {model_load_time:.2f} 秒 ({model_load_time*1000:.2f} 毫秒)")
    print(f"\n第一次推理（含预热）:")
    print(f"  总耗时: {first_inference_time:.2f} 秒 ({first_inference_time*1000:.2f} 毫秒)")
    if warmup_time > 0:
        print(f"  其中预热时间: {warmup_time:.2f} 秒 ({warmup_time*1000:.2f} 毫秒)")
        print(f"  实际推理时间: {avg_time:.2f} 秒 ({avg_time*1000:.2f} 毫秒)")
    
    print(f"\n后续推理统计（{num_runs} 次，不含预热）:")
    print(f"  平均耗时: {avg_time:.2f} 秒 ({avg_time*1000:.2f} 毫秒)")
    print(f"  最小耗时: {min_time:.2f} 秒 ({min_time*1000:.2f} 毫秒)")
    print(f"  最大耗时: {max_time:.2f} 秒 ({max_time*1000:.2f} 毫秒)")
    
    # 计算吞吐量（每秒处理的音频数量）
    throughput = 1.0 / avg_time if avg_time > 0 else 0
    print(f"  吞吐量: {throughput:.2f} 次/秒")
    
    # 预热时间占比
    if warmup_time > 0:
        warmup_ratio = (warmup_time / first_inference_time) * 100
        print(f"\n预热时间占比: {warmup_ratio:.1f}%")
    
    # 显存统计
    if torch.cuda.is_available():
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
        final_memory = torch.cuda.memory_allocated() / 1024**3  # GB
        final_reserved = torch.cuda.memory_reserved() / 1024**3  # GB
        
        # 获取全局峰值（从程序开始到现在的峰值）
        global_peak_allocated = torch.cuda.max_memory_allocated() / 1024**3  # GB
        global_peak_reserved = torch.cuda.max_memory_reserved() / 1024**3  # GB
        
        print("\n" + "="*60)
        print("显存使用统计:")
        print("="*60)
        print(f"GPU 总显存: {total_memory:.2f} GB")
        
        # 初始显存
        if initial_memory:
            print(f"\n初始显存占用: {initial_memory['allocated']:.2f} GB")
        
        # 模型加载后显存
        if after_load_memory:
            print(f"模型加载后显存: {after_load_memory['allocated']:.2f} GB (增加: {load_memory_increase:.2f} GB)")
        
        print(f"当前显存占用: {final_memory:.2f} GB")
        print(f"当前显存预留: {final_reserved:.2f} GB")
        print(f"\n峰值显存统计（全局最高）:")
        print(f"  峰值显存分配: {global_peak_allocated:.2f} GB")
        print(f"  峰值显存预留: {global_peak_reserved:.2f} GB")
        print(f"  峰值使用率: {(global_peak_allocated/total_memory)*100:.1f}%")
        
        # 多次推理的显存统计
        if inference_memory_peaks:
            avg_peak_mem = sum(inference_memory_peaks) / len(inference_memory_peaks)
            max_peak_mem = max(inference_memory_peaks)
            min_peak_mem = min(inference_memory_peaks)
            print(f"\n推理过程显存统计（{num_runs} 次）:")
            print(f"  平均峰值显存: {avg_peak_mem:.2f} GB")
            print(f"  最大峰值显存: {max_peak_mem:.2f} GB")
            print(f"  最小峰值显存: {min_peak_mem:.2f} GB")
        
        print("="*60)
    else:
        print("\n注意: 未检测到GPU，无法统计显存占用")
    
    print("="*60)