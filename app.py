from tkinter import *
from dpi_set import DpiManager
from pytubefix import YouTube
import os

def download_video():
    try:
        video_url = entry_link.get()
        if not video_url:
            return
        
        yt = YouTube(video_url)
        stream = yt.streams.get_highest_resolution()
        
        # Create Downloads folder if it doesn't exist
        if not os.path.exists("Downloads"):
            os.makedirs("Downloads")
        
        # Download the video
        stream.download(output_path="Downloads")
        print(f"Downloaded: {yt.title}")
        
    except Exception as e:
        print(f"Error: {e}")


# สร้าง DPI Manager และตั้งค่า DPI awareness
dpi = DpiManager()
dpi.enable_win_dpi_awareness()

# สร้างหน้าต่างหลัก
root = Tk()
root.title("Youtube Dowloader")

# สร้าง canvas และลงทะเบียนให้รองรับ DPI scaling
canvas = Canvas(root, width=400, height=200)
canvas.pack()

# ลงทะเบียน canvas ให้ปรับขนาดตาม DPI scaling
dpi.register_canvas_for_scaling(canvas, original_width=400, original_height=200)

# ทำให้หน้าต่างรองรับ DPI scaling
dpi.bind_auto_update(root)

#ชื่อโปรแกรม
app_title = Label(root, text="ดาวน์โหลดวิดีโอจาก Youtube", font=("Sarabun", 20, "bold"))
canvas.create_window(200, 50, window=app_title)
label_link = Label(root, text="ระบุลิงค์วิดีโอ (URL)", font=("Sarabun", 8))
canvas.create_window(200, 90, window=label_link)

#ระบุลิงค์วิดีโอ / ปุ่มดาวน์โหลด
entry_link = Entry(root, width=40, font=("Sarabun", 12))
canvas.create_window(200, 120, window=entry_link)

bt_download = Button(root, text="ดาวน์โหลด", font=("Sarabun", 10), width=10, height=1, command=download_video)
canvas.create_window(200, 170, window=bt_download)




# เริ่มต้นโปรแกรม
if __name__ == "__main__":
    root.mainloop()
