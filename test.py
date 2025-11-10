# coding=utf-8
"""
这是一个结合大语言模型(LLM)和文本转语音(TTS)的实时语音合成示例程序
功能：使用阿里云DashScope API实现LLM生成文本后，实时转换为语音并播放

依赖库安装说明：
"""
# Installation instructions for pyaudio:
# APPLE Mac OS X
#   brew install portaudio
#   pip install pyaudio
# Debian/Ubuntu
#   sudo apt-get install python-pyaudio python3-pyaudio
#   or
#   pip install pyaudio
# CentOS
#   sudo yum install -y portaudio portaudio-devel && pip install pyaudio
# Microsoft Windows
#   python -m pip install pyaudio

# 导入音频处理库，用于播放生成的语音
import pyaudio
# 导入阿里云DashScope SDK
import dashscope
# 导入TTS相关的类和函数
from dashscope.audio.tts_v2 import *

# 导入HTTP状态码，用于判断API调用是否成功
from http import HTTPStatus
# 导入Generation类，用于调用大语言模型生成文本
from dashscope import Generation

# API Key配置
# 若没有将API Key配置到环境变量中，需将下面这行代码注释放开，并将apiKey替换为自己的API Key
# dashscope.api_key = "apiKey"

# TTS模型配置
model = "cosyvoice-v2"  # 使用的语音合成模型名称
voice = "longxiaochun_v2"  # 使用的音色名称


class Callback(ResultCallback):
    """
    语音合成结果回调类
    继承自ResultCallback，用于处理TTS WebSocket连接的各种事件
    包括：连接打开、音频数据接收、任务完成、错误处理、连接关闭等
    """
    _player = None  # PyAudio播放器实例，用于初始化音频输出设备
    _stream = None  # 音频流对象，用于实际播放音频数据

    def on_open(self):
        """
        WebSocket连接打开时的回调函数
        当TTS服务连接成功时调用，初始化音频播放器
        """
        print("websocket is open.")
        # 创建PyAudio实例，用于音频播放
        self._player = pyaudio.PyAudio()
        # 打开音频输出流
        # format: 音频格式，paInt16表示16位整数格式
        # channels: 声道数，1表示单声道
        # rate: 采样率，22050Hz
        # output: True表示这是输出流（用于播放）
        self._stream = self._player.open(
            format=pyaudio.paInt16, channels=1, rate=22050, output=True
        )

    def on_complete(self):
        """
        语音合成任务完成时的回调函数
        当所有文本都已转换为语音并发送完成后调用
        """
        print("speech synthesis task complete successfully.")

    def on_error(self, message: str):
        """
        发生错误时的回调函数
        
        参数:
            message: 错误信息字符串
        """
        print(f"speech synthesis task failed, {message}")

    def on_close(self):
        """
        WebSocket连接关闭时的回调函数
        清理音频播放资源，释放系统资源
        """
        print("websocket is closed.")
        # 停止音频流播放
        self._stream.stop_stream()
        # 关闭音频流
        self._stream.close()
        # 终止PyAudio实例，释放资源
        self._player.terminate()

    def on_event(self, message):
        """
        接收到事件消息时的回调函数
        用于处理TTS服务发送的各种事件消息
        
        参数:
            message: 事件消息内容
        """
        print(f"recv speech synthsis message {message}")

    def on_data(self, data: bytes) -> None:
        """
        接收到音频数据时的回调函数
        这是核心函数，当TTS服务生成音频数据后，会调用此函数进行播放
        
        参数:
            data: 音频数据的字节流
        """
        print("audio result length:", len(data))
        # 将接收到的音频数据写入音频流，实现实时播放
        self._stream.write(data)


def synthesizer_with_llm():
    """
    主函数：结合LLM和TTS实现实时语音合成
    
    工作流程：
    1. 创建TTS合成器，配置回调函数
    2. 调用LLM生成文本（流式输出）
    3. 将LLM生成的文本片段实时转换为语音并播放
    4. 完成所有文本的语音合成
    """
    # 创建回调对象，用于处理TTS的各种事件
    callback = Callback()
    
    # 创建语音合成器实例
    # model: 使用的TTS模型
    # voice: 使用的音色
    # format: 音频格式，PCM格式，22050Hz采样率，单声道，16位
    # callback: 回调对象，用于接收音频数据和事件
    synthesizer = SpeechSynthesizer(
        model=model,
        voice=voice,
        format=AudioFormat.PCM_22050HZ_MONO_16BIT,
        callback=callback,
    )

    # 构建LLM的输入消息
    # role: "user"表示用户消息
    # content: 用户的问题或指令
    messages = [{"role": "user", "content": "请介绍一下你自己"}]
    
    # 调用大语言模型生成文本
    # model: 使用的LLM模型，qwen-turbo是通义千问的快速版本
    # messages: 对话消息列表
    # result_format: 返回格式为"message"，便于提取文本内容
    # stream: True表示启用流式输出，文本会分块返回，而不是等待全部生成完
    # incremental_output: True表示启用增量输出，每次返回新增的文本片段
    responses = Generation.call(
        model="qwen-turbo",
        messages=messages,
        result_format="message",  # 设置返回格式为消息格式
        stream=True,  # 启用流式输出
        incremental_output=True,  # 启用增量输出，实现真正的实时效果
    )
    
    # 遍历流式响应的每个文本片段
    for response in responses:
        # 检查响应状态码，判断是否成功
        if response.status_code == HTTPStatus.OK:
            # 提取生成的文本内容
            text_content = response.output.choices[0]["message"]["content"]
            # 打印文本内容（不换行，实现流式显示效果）
            print(text_content, end="")
            # 将文本片段实时转换为语音
            # 这是流式处理的核心：每收到一个文本片段就立即转换为语音
            # 而不是等待所有文本生成完再转换
            synthesizer.streaming_call(text_content)
        else:
            # 如果请求失败，打印错误信息
            print(
                "Request id: %s, Status code: %s, error code: %s, error message: %s"
                % (
                    response.request_id,  # 请求ID，用于问题追踪
                    response.status_code,  # HTTP状态码
                    response.code,  # 错误代码
                    response.message,  # 错误消息
                )
            )
    
    # 通知TTS合成器所有文本已发送完毕，可以完成最后的合成工作
    synthesizer.streaming_complete()
    # 打印本次TTS请求的ID，可用于日志记录和问题排查
    print('requestId: ', synthesizer.get_last_request_id())


if __name__ == "__main__":
    """
    程序入口
    当直接运行此脚本时，执行主函数
    """
    synthesizer_with_llm()