"""
使用 FunASR 进行语音识别
修复 CUDA 驱动初始化错误
"""

import sys
import os
import time

# 检查 CUDA 可用性
def check_cuda_availability():
    """检查 CUDA 是否可用，并提供详细的错误信息"""
    try:
        import torch
    except ImportError:
        print("错误: 未安装 PyTorch")
        print("请运行: pip install torch")
        sys.exit(1)
    
    # 检查 CUDA 是否可用
    if not torch.cuda.is_available():
        print("\n" + "="*60)
        print("警告: CUDA 不可用")
        print("="*60)
        print("可能的原因:")
        print("1. 没有安装 CUDA 驱动")
        print("2. CUDA 驱动版本与 PyTorch 不兼容")
        print("3. 系统没有 NVIDIA GPU")
        print("4. GPU 驱动未正确加载")
        print("\n解决方案:")
        print("1. 检查是否有 NVIDIA GPU:")
        print("   nvidia-smi")
        print("\n2. 如果 nvidia-smi 无法运行，需要安装 NVIDIA 驱动:")
        print("   # Ubuntu/Debian:")
        print("   sudo apt-get update")
        print("   sudo apt-get install nvidia-driver-xxx  # xxx 是驱动版本号")
        print("\n3. 检查 PyTorch 是否支持 CUDA:")
        print("   python -c 'import torch; print(torch.cuda.is_available())'")
        print("\n4. 如果 PyTorch 不支持 CUDA，需要安装支持 CUDA 的版本:")
        print("   # 访问 https://pytorch.org/ 获取正确的安装命令")
        print("   # 例如: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
        print("\n5. 如果确实没有 GPU，可以使用 CPU 运行:")
        print("   将 device='cuda:0' 改为 device='cpu'")
        print("="*60)
        
        # 尝试获取更详细的错误信息
        try:
            torch.cuda.init()
        except RuntimeError as e:
            print(f"\n详细错误信息: {e}")
            print("\n常见错误原因:")
            if "driver initialization failed" in str(e).lower():
                print("  • CUDA 驱动未安装或版本不兼容")
                print("  • 运行 'nvidia-smi' 检查驱动是否正常")
            elif "no cuda-capable device" in str(e).lower():
                print("  • 系统没有支持 CUDA 的 GPU")
            else:
                print(f"  • {e}")
        
        return False
    
    # CUDA 可用，显示信息
    print(f"✓ CUDA 可用")
    print(f"  GPU 数量: {torch.cuda.device_count()}")
    print(f"  当前 GPU: {torch.cuda.get_device_name(0)}")
    print(f"  CUDA 版本: {torch.version.cuda}")
    print(f"  cuDNN 版本: {torch.backends.cudnn.version()}")
    return True

# 检查 CUDA
cuda_available = check_cuda_availability()

# 显存统计函数
def get_memory_info():
    """获取显存信息"""
    import torch
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

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

model_dir = "iic/SenseVoiceSmall"

# 根据 CUDA 可用性选择设备
device = "cuda:0" if cuda_available else "cpu"
if not cuda_available:
    print("\n注意: 将使用 CPU 运行（速度较慢）")
    print("如果希望使用 GPU，请先解决 CUDA 问题\n")

# 初始化显存统计
if cuda_available:
    import torch
    torch.cuda.reset_peak_memory_stats()
    initial_memory = get_memory_info()
    if initial_memory:
        print(f"\n初始显存状态:")
        print(f"  当前分配: {initial_memory['allocated']:.2f} GB")
        print(f"  总显存: {initial_memory['total']:.2f} GB")

try:
    print(f"\n正在加载模型，使用设备: {device}...")
    model_load_start = time.perf_counter()
    model = AutoModel(
        model=model_dir,
        trust_remote_code=True,
        remote_code="./model.py",  
        vad_model="fsmn-vad",
        vad_kwargs={"max_single_segment_time": 30000},
        device=device,
    )
    model_load_end = time.perf_counter()
    model_load_time = model_load_end - model_load_start
    
    # 模型加载后的显存
    if cuda_available:
        after_load_memory = get_memory_info()
        if after_load_memory and initial_memory:
            load_memory_increase = after_load_memory['allocated'] - initial_memory['allocated']
            print(f"模型加载完成！耗时: {model_load_time:.2f} 秒 ({model_load_time*1000:.2f} 毫秒)")
            print(f"模型加载后显存: {after_load_memory['allocated']:.2f} GB (增加: {load_memory_increase:.2f} GB)")
        else:
            print(f"模型加载完成！耗时: {model_load_time:.2f} 秒 ({model_load_time*1000:.2f} 毫秒)")
    else:
        print(f"模型加载完成！耗时: {model_load_time:.2f} 秒 ({model_load_time*1000:.2f} 毫秒)")
except RuntimeError as e:
    if "cuda" in str(e).lower() or "driver initialization failed" in str(e).lower():
        print("\n" + "="*60)
        print("错误: CUDA 驱动初始化失败")
        print("="*60)
        print(f"详细错误: {e}")
        print("\n错误原因:")
        print("1. CUDA 驱动未安装或版本不兼容")
        print("   - 运行 'nvidia-smi' 检查驱动是否正常")
        print("   - 如果 nvidia-smi 无法运行，需要安装 NVIDIA 驱动")
        print("\n2. PyTorch 的 CUDA 版本与系统 CUDA 驱动不匹配")
        print("   - 检查 PyTorch 编译时的 CUDA 版本: python -c 'import torch; print(torch.version.cuda)'")
        print("   - 检查系统 CUDA 版本: nvcc --version 或 cat /usr/local/cuda/version.txt")
        print("   - 确保两者兼容")
        print("\n3. GPU 驱动未正确加载")
        print("   - 检查 /proc/driver/nvidia/version 是否存在")
        print("   - 尝试重启系统或重新加载驱动")
        print("\n4. 权限问题")
        print("   - 确保用户有权限访问 GPU 设备")
        print("\n解决方案:")
        print("1. 安装或更新 NVIDIA 驱动:")
        print("   # Ubuntu/Debian:")
        print("   sudo apt-get update")
        print("   sudo ubuntu-drivers autoinstall  # 自动安装推荐驱动")
        print("   # 或手动安装:")
        print("   sudo apt-get install nvidia-driver-535  # 根据你的 GPU 选择版本")
        print("\n2. 安装支持 CUDA 的 PyTorch:")
        print("   # 访问 https://pytorch.org/ 获取正确的安装命令")
        print("   # 确保 PyTorch 的 CUDA 版本与系统驱动兼容")
        print("\n3. 使用 CPU 运行（临时解决方案）:")
        print("   将 device='cuda:0' 改为 device='cpu'")
        print("="*60)
        sys.exit(1)
    else:
        raise

# 测试音频URL
test_audio_url = "https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/test_audio/asr_example_zh.wav"

print("\n" + "="*60)
print("开始测试推理性能")
print("="*60)

# 预热时间说明
print("\n" + "-"*60)
print("关于预热时间（Warm-up Time）:")
print("-"*60)
print("预热时间是指第一次推理时，模型需要执行的额外初始化操作，包括:")
print("  • GPU内存分配和初始化")
print("  • CUDA kernel编译（JIT编译）")
print("  • 运行时缓存初始化")
print("  • 其他一次性初始化操作")
print("因此第一次推理通常比后续推理慢，这就是'预热'的概念。")
print("-"*60)

# 第一次推理（包含预热时间）
print("\n第一次推理（包含预热时间）...")
if cuda_available:
    import torch
    torch.cuda.reset_peak_memory_stats()
    before_inference_memory = get_memory_info()

inference_start = time.perf_counter()
res = model.generate(
    input=test_audio_url,
    cache={},
    language="auto",  # "zn", "en", "yue", "ja", "ko", "nospeech"
    use_itn=True,
    batch_size_s=60,
    merge_vad=True,
    merge_length_s=15,
)
inference_end = time.perf_counter()
first_inference_time = inference_end - inference_start

text = rich_transcription_postprocess(res[0]["text"])
print(f"识别结果: {text}")
print(f"第一次推理耗时（含预热）: {first_inference_time:.2f} 秒 ({first_inference_time*1000:.2f} 毫秒)")

if cuda_available:
    after_inference_memory = get_memory_info()
    if after_inference_memory and before_inference_memory:
        inference_memory_increase = after_inference_memory['max_allocated'] - before_inference_memory['allocated']
        print(f"第一次推理显存峰值: {after_inference_memory['max_allocated']:.2f} GB (增加: {inference_memory_increase:.2f} GB)")

# 多次推理计算平均时间（排除第一次预热）
print("\n进行多次推理以计算平均耗时（排除第一次预热）...")
print("这些推理时间代表模型在实际使用中的真实性能。")
num_runs = 5
inference_times = []
inference_memory_peaks = []

for i in range(num_runs):
    if cuda_available:
        import torch
        torch.cuda.reset_peak_memory_stats()
        before_memory = get_memory_info()
    
    inference_start = time.perf_counter()
    res = model.generate(
        input=test_audio_url,
        cache={},
        language="auto",
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )
    inference_end = time.perf_counter()
    inference_time = inference_end - inference_start
    inference_times.append(inference_time)
    
    if cuda_available:
        after_memory = get_memory_info()
        if after_memory:
            peak_memory = after_memory['max_allocated']
            inference_memory_peaks.append(peak_memory)
            current_memory = after_memory['allocated']
            print(f"  第 {i+1} 次推理: {inference_time*1000:.2f} 毫秒 | 显存: {current_memory:.2f} GB (峰值: {peak_memory:.2f} GB)")
        else:
            print(f"  第 {i+1} 次推理: {inference_time*1000:.2f} 毫秒")
    else:
        print(f"  第 {i+1} 次推理: {inference_time*1000:.2f} 毫秒")

# 统计信息
if inference_times:
    avg_time = sum(inference_times) / len(inference_times)
    min_time = min(inference_times)
    max_time = max(inference_times)
    
    # 计算预热时间
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
    
    # 计算吞吐量
    throughput = 1.0 / avg_time if avg_time > 0 else 0
    print(f"  吞吐量: {throughput:.2f} 次/秒")
    
    # 预热时间占比
    if warmup_time > 0:
        warmup_ratio = (warmup_time / first_inference_time) * 100
        print(f"\n预热时间占比: {warmup_ratio:.1f}%")
    
    # 显存统计
    if cuda_available:
        import torch
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
        final_memory = torch.cuda.memory_allocated() / 1024**3  # GB
        final_reserved = torch.cuda.memory_reserved() / 1024**3  # GB
        
        # 获取全局峰值
        global_peak_allocated = torch.cuda.max_memory_allocated() / 1024**3  # GB
        global_peak_reserved = torch.cuda.max_memory_reserved() / 1024**3  # GB
        
        print("\n" + "="*60)
        print("显存使用统计:")
        print("="*60)
        print(f"GPU 总显存: {total_memory:.2f} GB")
        
        if initial_memory:
            print(f"\n初始显存占用: {initial_memory['allocated']:.2f} GB")
        
        if after_load_memory:
            print(f"模型加载后显存: {after_load_memory['allocated']:.2f} GB")
        
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