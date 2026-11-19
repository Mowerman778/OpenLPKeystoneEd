"""
Reproducer: soffice.bin crashes in d3d9.dll while an Impress slide show started through the UNO API plays a video.

Run with LibreOffice's bundled Python (Windows):
    "C:\\Program Files\\LibreOffice\\program\\soffice.exe" --norestore --nologo --nodefault ^
        "--accept=socket,host=localhost,port=2002;urp;"
    "C:\\Program Files\\LibreOffice\\program\\python.exe" repro_api_slideshow_video.py C:\\path\\to\\clip_640x360_20s.mp4

The script creates a 2-slide presentation (slide 2 holds the video), starts the slide show, moves to slide 2
and then waits 30 seconds while checking that soffice.bin is still running.
"""
import subprocess
import sys
import time
from pathlib import Path

import uno
from com.sun.star.awt import Point, Size
from com.sun.star.beans import PropertyValue


def prop(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def soffice_running():
    return b'soffice.bin' in subprocess.run(['tasklist'], capture_output=True).stdout


clip = Path(sys.argv[1]).resolve()
ctx = uno.getComponentContext()
resolver = ctx.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', ctx)
for _ in range(40):
    try:
        remote = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
        break
    except Exception:
        time.sleep(0.5)
desktop = remote.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop', remote)

doc = desktop.loadComponentFromURL('private:factory/simpress', '_blank', 0, ())
pages = doc.getDrawPages()
text = doc.createInstance('com.sun.star.drawing.TextShape')
pages.getByIndex(0).add(text)
text.setSize(Size(20000, 3000))
text.setPosition(Point(2000, 5000))
text.setString('Slide 1 - the next slide has a video')
video_page = pages.insertNewByIndex(0)
media = doc.createInstance('com.sun.star.presentation.MediaShape')
video_page.add(media)
media.setSize(Size(20000, 11250))
media.setPosition(Point(2000, 2000))
media.setPropertyValue('MediaURL', clip.as_uri())

presentation = doc.getPresentation()
presentation.start()
controller = None
while not controller:
    time.sleep(0.1)
    controller = presentation.getController()
time.sleep(2)
controller.gotoSlideIndex(1)
print('Slide show is on the video slide')

start = time.time()
while time.time() - start < 30:
    time.sleep(0.5)
    if not soffice_running():
        print('soffice.bin CRASHED {:.1f} s after showing the video slide'.format(time.time() - start))
        sys.exit(1)
print('No crash within 30 s')
presentation.end()
doc.close(True)
