import pygame
import numpy as np
import librosa
import moviepy.editor as mpy
import os

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
        self.y, self.sr = librosa.load(audio_path)
        self.stft = np.abs(librosa.stft(self.y))
        self.frequencies = librosa.core.fft_frequencies(sr=self.sr)
        self.times = librosa.core.frames_to_time(range(self.stft.shape[1]), sr=self.sr)

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
        self.load_audio(audio_path)
        duration = librosa.get_duration(y=self.y, sr=self.sr)
        fps = 30
        total_frames = int(duration * fps)

        def make_frame(t):
            frame_index = int(t * fps)
            return self.draw_frame(frame_index)

        animation = mpy.VideoClip(make_frame, duration=duration)
        animation.write_videofile(output_path, fps=fps)

def main():
    visualizer = MusicVisualizer()
    # 设置输入输出路径
    audio_path = 'input.mp3'  # 用户需要将音频文件重命名为input.mp3
    output_path = 'output.mp4'
    
    if not os.path.exists(audio_path):
        print(f'请将音频文件重命名为{audio_path}并放在程序同目录下')
        return

    print('开始生成音乐可视化视频...')
    visualizer.create_animation(audio_path, output_path)
    print(f'视频已生成: {output_path}')

if __name__ == '__main__':
    main()