import pygame
import numpy as np
import librosa
import cv2
import os
from utils.logger import logger

class MusicVisualizer:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.bg_color = (0, 0, 0)
        self.ball_color = (255, 255, 255)
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('音乐可视化')

    def load_audio(self, audio_path):
        # 加载音频文件并进行预处理
        logger.info(f'开始加载音频文件: {audio_path}')
        self.y, self.sr = librosa.load(audio_path)
        self.stft = np.abs(librosa.stft(self.y))
        self.frequencies = librosa.core.fft_frequencies(sr=self.sr)
        self.times = librosa.core.frames_to_time(range(self.stft.shape[1]), sr=self.sr)
        logger.info('音频文件加载完成')

    def get_frequency_bands(self, frame_index):
        # 获取当前帧的频率数据
        if frame_index >= self.stft.shape[1]:
            return np.zeros(10)
        magnitudes = self.stft[:, frame_index]
        # 将频率分为10个波段
        bands = np.array_split(magnitudes, 10)
        return np.array([np.mean(band) for band in bands])

    def draw_frame(self, frame_index):
        # 绘制单帧画面
        self.screen.fill(self.bg_color)
        bands = self.get_frequency_bands(frame_index)
        max_magnitude = np.max(bands)
        if max_magnitude > 0:
            bands = bands / max_magnitude

        for i, magnitude in enumerate(bands):
            # 计算小球位置和大小
            x = self.width * (i + 1) / (len(bands) + 1)
            y = self.height / 2 + magnitude * 100 * np.sin(frame_index * 0.1)
            radius = 20 + magnitude * 30
            
            # 根据频率设置颜色
            color = (int(255 * magnitude), 
                    int(100 + 155 * magnitude), 
                    int(200 * (1 - magnitude)))
            
            # 绘制小球
            pygame.draw.circle(self.screen, color, (int(x), int(y)), int(radius))

        pygame.display.flip()
        return pygame.surfarray.array3d(self.screen)

    def create_animation(self, audio_path, output_path):
        logger.info('开始创建音乐可视化动画')
        self.load_audio(audio_path)
        duration = librosa.get_duration(y=self.y, sr=self.sr)
        fps = 30
        total_frames = int(duration * fps)
        logger.info(f'视频总帧数: {total_frames}, 时长: {duration:.2f}秒')
        
        # 尝试不同的编码器
        codecs = ['mp4v', 'avc1', 'H264']
        video = None
        
        # 确保输出路径是绝对路径
        if not os.path.isabs(output_path):
            output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_path)
        
        # 尝试不同的编码器直到成功
        for codec in codecs:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                video = cv2.VideoWriter(output_path, fourcc, float(fps), (self.width, self.height))
                if video.isOpened():
                    logger.info(f'成功使用编码器 {codec}')
                    break
            except Exception as e:
                logger.warning(f'编码器 {codec} 初始化失败: {str(e)}')
                if video is not None:
                    video.release()
        
        if not video.isOpened():
            error_msg = f'无法创建视频写入器，请检查编码器是否支持或输出路径是否正确: {output_path}'
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 逐帧生成并写入视频
        logger.info('开始生成视频帧')
        for frame_index in range(total_frames):
            if frame_index % 100 == 0:  # 每100帧记录一次进度
                logger.debug(f'正在处理第 {frame_index}/{total_frames} 帧')
            frame = self.draw_frame(frame_index)
            
            # 验证帧数据
            if frame is None or frame.size == 0:
                logger.error(f'第 {frame_index} 帧数据无效')
                continue
                
            # 确保帧数据类型和尺寸正确
            frame = frame.astype(np.uint8)
            if frame.shape[:2] != (self.height, self.width):
                logger.warning(f'第 {frame_index} 帧尺寸不正确，进行调整')
                frame = cv2.resize(frame, (self.width, self.height))
            
            # 将RGB转换为BGR格式
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            try:
                video.write(frame)
            except Exception as e:
                logger.error(f'写入第 {frame_index} 帧时出错: {str(e)}')
                continue
        
        video.release()
        logger.info(f'视频生成完成: {output_path}')
        
        # 使用ffmpeg合并音频和视频
        temp_video = output_path + '.temp.mp4'
        os.rename(output_path, temp_video)
        try:
            # 使用ffmpeg将音频合并到视频中
            ffmpeg_cmd = f'ffmpeg -i {temp_video} -i {audio_path} -c:v copy -c:a aac -strict experimental {output_path}'
            os.system(ffmpeg_cmd)
            os.remove(temp_video)  # 删除临时文件
            logger.info('音频合并完成')
        except Exception as e:
            logger.error(f'音频合并失败: {str(e)}')
            # 如果合并失败，恢复原视频文件
            if os.path.exists(temp_video):
                os.rename(temp_video, output_path)

def main():
    try:
        visualizer = MusicVisualizer()
        # 设置输入输出路径
        downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'downloads')
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取downloads目录中的音频文件
        audio_files = [f for f in os.listdir(downloads_dir) if f.endswith(('.mp3', '.wav', '.ogg'))]
        
        if not audio_files:
            logger.error(f'在 {downloads_dir} 目录中未找到音频文件')
            return
            
        for audio_file in audio_files:
            audio_path = os.path.join(downloads_dir, audio_file)
            # 使用相同的文件名（但改为mp4扩展名）作为输出文件名
            output_filename = os.path.splitext(audio_file)[0] + '.mp4'
            output_path = os.path.join(output_dir, output_filename)
            
            logger.info(f'处理音频文件: {audio_file}')
            visualizer.create_animation(audio_path, output_path)
    except Exception as e:
        logger.error(f'程序执行出错: {str(e)}')
        raise

if __name__ == '__main__':
    main()