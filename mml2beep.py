# -*- coding: utf-8 -*-

import argparse, json, os
from time import sleep

is_windows = "nt" in os.name

if is_windows:
    try:
        import InpOut32
    except:
        pass
else:
    import fcntl, termios, os
    beep_device = os.open("/dev/console", os.O_WRONLY)

class MmlParser:
    """MML语法参考：https://mabinogi.fws.tw/ac_com_annzyral.php"""

    # 音程 -> 音阶 -> 频率，按十二平均律算
    FREQ_TABLE = [
        [16.35, 17.32, 18.35, 19.45, 20.6, 21.83, 23.12, 24.5, 25.96, 27.5, 29.14, 30.87],          # C0~B0（未使用）
        [32.7, 34.65, 36.71, 38.89, 41.2, 43.65, 46.25, 49, 51.91, 55, 58.27, 61.74],               # C1~B1
        [65.41, 69.3, 73.42, 77.78, 82.41, 87.31, 92.5, 98, 103.83, 110, 116.54, 123.47],
        [130.81, 138.59, 146.83, 155.56, 164.81, 174.61, 185, 196, 207.65, 220, 233.08, 246.94],
        [261.63, 277.18, 293.66, 311.13, 329.63, 349.23, 369.99, 392, 415.3, 440, 466.16, 493.88],  # C4~B4
        [523.25, 554.37, 587.33, 622.25, 659.26, 698.46, 739.99, 783.99, 830.61, 880, 932.33, 987.77],
        [1046.5, 1108.73, 1174.66, 1244.51, 1318.51, 1396.91, 1479.98, 1567.98, 1661.22, 1760, 1864.66, 1975.53],
        [2093, 2217.46, 2349.32, 2489.02, 2637.02, 2793.83, 2959.96, 3135.96, 3322.44, 3520, 3729.31, 3951.07],
        [4186.01, 4434.92, 4698.64, 4978.03, 5274.04, 5587.65, 5919.91, 6271.92, 6644.87, 7039.99, 7458.61, 7902.12]
    ]

    # 字符 -> 音阶索引
    SCALE = {
        'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11
    }

    def __init__(self):
        # MML字符串
        self._mml = ''
        # 当前MML字符串索引
        self._index = 0
        # 当前输出音轨
        self._output = []
        # 音轨数组
        self._res = [self._output]

        # 音程
        self._octave = 4
        # 音程强制偏移量
        self._octave_shift = 0
        # 预设音长（几分音符，4分音符为1拍）
        self._default_length = 4
        # 速度（BPM，一分钟几拍）
        self._tempo = 120

    """ 设置相对音程 """
    def shift_octave(self, value):
        self._octave_shift = value
        return self

    def parse(self, mml):
        """转换MML乐谱到beep谱

        返回音轨数组，每个音轨包含多个音符，每个音符为[频率(Hz), 持续时间(ms)]，频率为0代表延时
        """

        self._mml = mml.upper()
        self._index = 0
        if self._mml.startswith('MML@'):
            self._index += 4
        self._output = []
        self._res = [self._output]

        self._octave = 4
        self._default_length = 4
        self._tempo = 120

        while self._index < len(self._mml):
            if self._mml[self._index] == ',':
                # 新音轨
                self._index += 1
                self._output = []
                self._res.append(self._output)

            elif self._mml[self._index] == ';':
                # 结束
                self._index += 1
                break

            elif self._mml[self._index] in 'CDEFGAB':
                # 音符
                self._output.append(self._read_note())

            elif self._mml[self._index] == 'R':
                # 休止符
                self._output.append(self._read_pause())

            elif self._mml[self._index] == '&':
                # 连接
                self._index += 1
                note = self._read_note()
                assert len(self._output) > 0, f'index = {self._index}，缺少被连接的音符'
                assert note[0] == self._output[-1][0], (f'index = {self._index}，'
                                                        f'{note[0]} != {self._output[-1][0]}，连接的音符音高不同')
                self._output[-1][1] += note[1]

            elif self._mml[self._index] == 'L':
                # 预设音长
                self._index += 1
                self._default_length = self._read_length() or 4

            elif self._mml[self._index] == 'T':
                # 播放速度
                # 暂时没有考虑三和弦共用
                self._index += 1
                tempo = self._read_number() or 120
                assert 32 <= tempo <= 255, f'index = {self._index}，tempo = {tempo}，速度超出范围'
                self._tempo = tempo

            elif self._mml[self._index] == 'V':
                # 音量（未使用）
                self._index += 1
                self._read_number()

            elif self._mml[self._index] == 'O':
                # 绝对音程
                self._index += 1
                octave = self._read_number() or 4
                assert 1 <= octave <= 8, f'index = {self._index}，octave = {octave}，音程超出范围'
                self._octave = octave

            elif self._mml[self._index] in '><':
                # 相对音程
                if self._mml[self._index] == '>':
                    self._octave += 1
                else:
                    self._octave -= 1
                assert 1 <= self._octave <= 8, f'index = {self._index}，octave = {octave}，音程超出范围'
                self._index += 1

            elif self._mml[self._index] == 'N':
                # 绝对音高
                self._output.append(self._read_abs_note())

            elif self._mml[self._index] in ' \t\r\n':
                # 空白
                self._index += 1

            else:
                # 错误
                assert False, f'index = {self._index}，未预料到的字符：{self._mml[self._index]}'

        return self._res

    def _read_number(self):
        """读数字，非数字则返回None"""

        if self._index >= len(self._mml) or not '0' <= self._mml[self._index] <= '9':
            return None
        res = 0
        while self._index < len(self._mml) and '0' <= self._mml[self._index] <= '9':
            res = res * 10 + int(self._mml[self._index])
            self._index += 1
        return res

    def _read_length(self):
        """读音长，默认音长则返回None"""

        length = self._read_number()
        if self._index < len(self._mml) and self._mml[self._index] == '.':
            if length is None:
                length = self._default_length / 1.5
            else:
                length /= 1.5
            self._index += 1
        return length

    def _read_note(self):
        """读音符"""

        octave = self._octave
        # 音阶索引
        scale = self.SCALE[self._mml[self._index]]
        self._index += 1
        if self._index < len(self._mml):
            if self._mml[self._index] in '+#':
                scale += 1
                self._index += 1
                if scale >= 12:
                    scale = 0
                    octave += 1
            elif self._mml[self._index] == '-':
                scale -= 1
                self._index += 1
                if scale < 0:
                    scale = 11
                    octave -= 1
            assert 0 <= scale < 12, f'index = {self._index}，scale = {scale}，音阶超出范围'
            assert 1 <= octave <= 8, f'index = {self._index}，octave = {octave}，音程超出范围'

        # 音长（几分音符）
        length = self._read_length() or self._default_length

        frequency = int(self.FREQ_TABLE[octave + self._octave_shift][scale])
        duration = int(60 / self._tempo * 4 / length * 1000)
        return [frequency, duration]

    def _read_pause(self):
        """读休止符"""

        self._index += 1

        # 音长（几分音符）
        length = self._read_length() or self._default_length

        duration = int(60 / self._tempo * 4 / length * 1000)
        return [0, duration]

    def _read_abs_note(self):
        """读绝对音高"""

        self._index += 1
        abs_note = self._read_number()
        assert 1 <= abs_note <= 96, f'index = {self._index}，abs_note = {abs_note}，绝对音高超出范围'

        abs_note -= 1
        scale = abs_note % 12
        octave = abs_note // 12 + 1
        frequency = int(self.FREQ_TABLE[octave][scale])
        duration = int(60 / self._tempo * 4 / self._default_length * 1000)
        return [frequency, duration]

def beep(freq, dura):
    """ For further info please see https://wiki.osdev.org/PC_Speaker  """
    """ Linux https://eadmaster.altervista.org/pub/prj/cliapps/beep.py """
    if freq > 0:
        cycle = int(1193180 / freq)
        if is_windows:
            InpOut32.DlPortWritePortUchar(67, 182)
            InpOut32.DlPortWritePortUchar(66, (cycle & 255))
            InpOut32.DlPortWritePortUchar(66, ((cycle >> 8) & 255))
            tmp = InpOut32.DlPortReadPortUchar(97)
            InpOut32.DlPortWritePortUchar(97, (tmp | 3))
        else:
            global beep_device
            fcntl.ioctl(beep_device, 19247, cycle)
    sleep(dura / 1000)
    if is_windows:
        tmp = InpOut32.DlPortReadPortUchar(97)
        InpOut32.DlPortWritePortUchar(97, (tmp & 252))
    else:
        fcntl.ioctl(beep_device, 19247, 0)

def main():
    parser = argparse.ArgumentParser(description='转换MML乐谱到beep谱')
    parser.add_argument('mml_file', default=None, nargs='?', help='输入的 MML 文件，格式为 txt . 若省略则使用标准输入流读取数据.')
    parser.add_argument('beep_file', default=None, nargs='?', help='输出的 beep 文件路径, 格式为 JSON . 其中第一个数为频率 (Hz) , 如果为 0 则表示延时. 第二个数为持续时间 (ms) . 若省略则输出到标准输出流.')
    parser.add_argument('-t', '--track', type=int, default=1, help='输出第几个音轨，默认为 1 ')
    parser.add_argument('-s', '--split', action="store_true", help='将所有频率与持续时间拆分为两个数组输出')
    parser.add_argument('-o', '--octave', type=int, default=0, help='将输出数据整体移动八度, 可取值 -2 ~ 2, 正为上移 (更高音) 负为下移 (更低音)')
    parser.add_argument('-p', '--play', action="store_true", help='直接通过 PC 喇叭实时播放乐谱, beep_file 与 --split 参数将无效. Windows 下需要 InpOut32 库支持且首次需要以管理员权限运行以安装驱动; Linux 下必须使用 root 权限运行.')

    args = parser.parse_args()
    args.track -= 1
    if abs(args.octave) > 2:
        raise ValueError("八度移动超出范围, 允许的值在 -2 ~ 2 之间")

    if not args.mml_file:
        mml = input("请粘贴 MML 格式数据, 使用换行符结束 >>> ")
        print()
    else:
        with open(args.mml_file) as f:
            mml = f.read()
            
    res = MmlParser().shift_octave(args.octave).parse(mml)
    track_data = res[args.track]

    if args.play:
        if is_windows:
            try:
                if not InpOut32.IsInpOutDriverOpen():
                    raise IOError("无法打开 InpOut32 驱动, 请使用管理员权限运行一次以安装驱动!")
            except:
                raise IOError("无法找到 InpOut32 动态链接库, 请确保 'inpout32.dll' 与 'inpoutx64.dll' 与脚本处在同一目录下!")
        for item in track_data:
            print(item)
            try:
                beep(item[0], item[1])
            except KeyboardInterrupt:
                beep(0, 0)
                if not is_windows:
                    os.close(beep_device)
                break
    else:
        ret = json.dumps(args.split and [list(t) for t in zip(*track_data)] or track_data)
        if args.beep_file:
            with open(args.beep_file, 'w') as f:
                f.write(ret)
        else:
            print(ret)

if __name__ == '__main__':
    main()
