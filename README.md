# mml2beep
Converts MML to beep music score. 转换MML乐谱到beep谱

MML (Music Macro Language) 是一些在线游戏（如洛奇）的乐谱代码

beep谱指以 `[频率, 持续时间]` 表示一个音符的乐谱, 用于蜂鸣器播放音乐

若需要使用直接播放功能, 请将 [`inpout32.dll` 与 `inpoutx64.dll`](http://www.highrez.co.uk/downloads/inpout32/) 复制到脚本同一目录下.

## 用法

```
usage: mml2beep.py [-h] [-t TRACK] [-s] [-o OCTAVE] [-p]
                   [mml_file] [beep_file]

转换MML乐谱到beep谱

positional arguments:
  mml_file              输入的 MML 文件，格式为 txt . 若省略则使用标准输入流读取数据.
  beep_file             输出的 beep 文件路径, 格式为 JSON . 其中第一个数为频率 (Hz) , 如果为 0
                        则表示延时. 第二个数为持续时间 (ms) . 若省略则输出到标准输出流.

optional arguments:
  -h, --help            show this help message and exit
  -t TRACK, --track TRACK
                        输出第几个音轨，默认为 1
  -s, --split           将所有频率与持续时间拆分为两个数组输出
  -o OCTAVE, --octave OCTAVE
                        将输出数据整体移动八度, 可取值 -2 ~ 2, 正为上移 (更高音) 负为下移 (更低音)
  -p, --play            直接通过 PC 喇叭实时播放乐谱, beep_file 与 --split 参数将无效. Windows
                        下需要 InpOut32 库支持且首次需要以管理员权限运行以安装驱动; Linux 下必须使用 root
                        权限运行.
```

## 链接

* [MML语法参考](https://mabinogi.fws.tw/ac_com_annzyral.php)
* [获取MML乐谱](https://mabinogi.fws.tw/ac_comproser.php)
