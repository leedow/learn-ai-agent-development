# AI桌面虚拟角色开发知识库

本知识库专注于使用Electron + Python技术栈开发AI桌面虚拟角色应用的相关知识。

## 技术架构
- **前端**: Electron桌面应用 + Live2D虚拟角色显示
- **后端**: Python服务端处理音频流、语音识别、LLM调用、语音合成
- **通信**: WebSocket实时音频流传输

## 知识库目录

### [01-项目架构与设计](./01-项目架构与设计/README.md)
- [项目架构与设计](./01-项目架构与设计/README.md)

### [02-Electron桌面端开发](./02-Electron桌面端开发/README.md)
- [Electron桌面端开发](./02-Electron桌面端开发/README.md)

### [03-Live2D虚拟角色集成](./03-Live2D虚拟角色集成/README.md)
- [Live2D虚拟角色集成](./03-Live2D虚拟角色集成/README.md)

### [04-音频录制与播放](./04-音频录制与播放/README.md)
- [音频录制与播放](./04-音频录制与播放/README.md)
- [音频采集的基础知识](./04-音频录制与播放/音频采集的基础知识.md)
- [AudioWorklet（Renderer）和本地 native 采集的区别](./04-音频录制与播放/AudioWorklet（Renderer）和本地%20native%20采集的区别.md)
- [MediaRecorder和其他方法对比](./04-音频录制与播放/MediaRecorder和其他方法对比.md)
- [使用electron开发桌面虚拟角色，录音实时对话，考虑高性能低延迟的需求，录音部分应该如何实现？](./04-音频录制与播放/使用electron开发桌面虚拟角色，录音实时对话，考虑高性能低延迟的需求，录音部分应该如何实现？.md)

### [05-WebSocket通信](./05-WebSocket通信/README.md)
- [WebSocket通信](./05-WebSocket通信/README.md)

### [06-Python服务端开发](./06-Python服务端开发/README.md)
- [Python服务端开发](./06-Python服务端开发/README.md)

### [07-语音识别技术](./07-语音识别技术/README.md)
- [语音识别技术](./07-语音识别技术/README.md)

### [08-大语言模型集成](./08-大语言模型集成/README.md)
- [大语言模型集成](./08-大语言模型集成/README.md)
- [总结推理框架的作用以及为什么要使用推理框架](./08-大语言模型集成/总结推理框架的作用以及为什么要使用推理框架.md)
- [对于支持KV CACHE的LLM连续对话功能是否需要把LLM给出的回复作为PROMPT作为增量提示词给LLM](./08-大语言模型集成/对于支持KV%20CACHE的LLM连续对话功能是否需要把LLM给出的回复作为PROMPT作为增量提示词给LLM.md)
- [kvcache_and_prompt](./08-大语言模型集成/kvcache_and_prompt.md)

### [09-语音合成技术](./09-语音合成技术/README.md)
- [语音合成技术](./09-语音合成技术/README.md)

### [10-部署与优化](./10-部署与优化/README.md)
- [部署与优化](./10-部署与优化/README.md)

### [11-开发工具与环境](./11-开发工具与环境/README.md)
- [开发工具与环境](./11-开发工具与环境/README.md)

### [12-常见问题与解决方案](./12-常见问题与解决方案/README.md)
- [常见问题与解决方案](./12-常见问题与解决方案/README.md)

## 项目说明

### 注意
本项目目录结构完全由AI规划生成，文档知识内容完全由AI问答生成