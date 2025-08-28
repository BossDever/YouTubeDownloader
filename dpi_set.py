# --- Universal DPI-friendly Tkinter Manager (drop-in solution) -------------
import platform
import ctypes
import tkinter as tk
import tkinter.font as tkFont


class DpiManager:
    """
    Universal DPI Manager สำหรับ Tkinter
    รองรับการย้ายข้ามจอที่มีความละเอียดต่างกัน
    ใช้ได้กับทุกโปรเจค - เพียงแค่ import และใช้งาน
    
    วิธีใช้:
        dpi = DpiManager()
        dpi.setup_dpi_awareness()
        root = tk.Tk()
        dpi.make_dpi_aware(root)
    """
    
    def __init__(self):
        self._windows_scaling_factor = self._get_windows_scaling_factor()
        self._last_dpi = None
        self._debounce_id = None
        self._monitor_change_callback = None
        self._is_dpi_aware = False
        
    def _get_windows_scaling_factor(self):
        """ดึง Windows scaling factor ปัจจุบัน"""
        if platform.system() != "Windows":
            return 1.0
            
        try:
            # ดึง DPI ของ primary monitor
            hdc = ctypes.windll.user32.GetDC(0)
            dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
            return dpi_x / 96.0
        except Exception:
            return 1.0
    
    def setup_dpi_awareness(self, mode="system_aware"):
        """
        ตั้งค่า DPI awareness สำหรับ Windows
        
        Args:
            mode: "system_aware" (แนะนำ) หรือ "per_monitor_aware"
        """
        if platform.system() != "Windows":
            return
            
        try:
            if mode == "per_monitor_aware":
                # Per-monitor DPI aware v2 (Windows 10 1703+)
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
                    self._is_dpi_aware = True
                    return
                except Exception:
                    pass
                    
                # Per-monitor DPI aware v1 (fallback)
                try:
                    DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE = ctypes.c_void_p(-3)
                    ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE)
                    self._is_dpi_aware = True
                    return
                except Exception:
                    pass
            
            # System DPI aware (เสถียรที่สุด - แนะนำ)
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
                self._is_dpi_aware = True
                return
            except Exception:
                pass
                
            # Legacy DPI aware (fallback สำหรับ Windows เก่า)
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                self._is_dpi_aware = True
            except Exception:
                pass
                
        except Exception:
            print("Warning: Could not set DPI awareness")
    
    def _get_window_dpi(self, root):
        """ดึง DPI ปัจจุบันของหน้าต่าง"""
        if platform.system() == "Windows":
            try:
                hwnd = root.winfo_id()
                dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
                return float(dpi) if dpi else 96.0
            except Exception:
                return 96.0
        else:
            # macOS/Linux
            try:
                return float(root.winfo_fpixels('1i'))
            except Exception:
                return 96.0
    
    def _get_monitor_handle(self, root):
        """ดึง monitor handle ของหน้าต่าง (Windows เท่านั้น)"""
        if platform.system() != "Windows":
            return None
            
        try:
            hwnd = root.winfo_id()
            return ctypes.windll.user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        except Exception:
            return None
    
    def _calculate_optimal_scaling(self, current_dpi):
        """คำนวณค่า scaling ที่เหมาะสมสำหรับ Tkinter"""
        if not self._is_dpi_aware:
            # ถ้าไม่ได้เปิด DPI awareness ให้ใช้ค่าเริ่มต้น
            return 1.0
            
        # สำหรับ Windows ที่เปิด DPI awareness
        if platform.system() == "Windows":
            # คำนวณ scaling factor โดยเทียบกับ 96 DPI (100%)
            base_scaling = current_dpi / 96.0
            
            # ปรับค่าให้เหมาะสมกับ Tkinter
            # Tkinter มีพฤติกรรมแปลกๆ กับ scaling บางค่า
            if base_scaling <= 1.0:
                return 1.0  # ไม่ scale ลงถ้าน้อยกว่าหรือเท่ากับ 100%
            elif base_scaling <= 1.25:
                return base_scaling  # 125% ใช้ค่าตรง
            elif base_scaling <= 1.5:
                return base_scaling * 0.95  # 150% ลดลงเล็กน้อย
            elif base_scaling <= 2.0:
                return base_scaling * 0.9  # 200% ลดลงมากขึ้น
            else:
                return 1.8  # จำกัดสูงสุดที่ 180%
        else:
            # macOS/Linux
            return max(0.8, min(2.0, current_dpi / 96.0))
    
    def _apply_scaling(self, root):
        """ปรับ scaling ของ Tkinter"""
        current_dpi = self._get_window_dpi(root)
        current_monitor = self._get_monitor_handle(root)
        
        # ตรวจสอบว่าเปลี่ยนจอหรือไม่
        monitor_changed = hasattr(self, '_last_monitor') and self._last_monitor != current_monitor
        dpi_changed = self._last_dpi != current_dpi
        
        if dpi_changed or monitor_changed or self._last_dpi is None:
            scaling = self._calculate_optimal_scaling(current_dpi)
            
            try:
                root.tk.call('tk', 'scaling', scaling)
                print(f"DPI: {current_dpi:.1f}, Scaling: {scaling:.2f}")
                
                # ปรับขนาด canvas ที่ลงทะเบียนไว้
                if hasattr(self, '_registered_canvases'):
                    for canvas in self._registered_canvases:
                        try:
                            if canvas.winfo_exists():  # ตรวจสอบว่า canvas ยังอยู่
                                canvas.resize_canvas(scaling)
                        except Exception as canvas_error:
                            print(f"Canvas resize error: {canvas_error}")
                            
            except Exception as e:
                print(f"Failed to apply scaling: {e}")
            
            self._last_dpi = current_dpi
            self._last_monitor = current_monitor
            
            # เรียก callback ถ้ามี
            if monitor_changed and self._monitor_change_callback:
                try:
                    monitor_info = {
                        'dpi': current_dpi,
                        'scaling': scaling,
                        'handle': current_monitor
                    }
                    self._monitor_change_callback(root, monitor_info)
                except Exception as e:
                    print(f"Monitor callback error: {e}")
    
    def make_dpi_aware(self, root, enable_auto_adjust=True):
        """
        ทำให้หน้าต่าง root รองรับ DPI scaling
        
        Args:
            root: Tkinter root window
            enable_auto_adjust: เปิดการปรับอัตโนมัติเมื่อย้ายจอ
        """
        # ปรับ scaling เริ่มต้น
        root.after(10, lambda: self._apply_scaling(root))
        
        if enable_auto_adjust:
            def _on_configure(event):
                if event.widget == root:  # เฉพาะ root window
                    if self._debounce_id:
                        root.after_cancel(self._debounce_id)
                    self._debounce_id = root.after(200, lambda: self._apply_scaling(root))
            
            root.bind('<Configure>', _on_configure)
            root.bind('<Map>', lambda e: self._apply_scaling(root))
    
    def set_monitor_change_callback(self, callback):
        """ตั้งค่า callback เมื่อเปลี่ยนจอ"""
        self._monitor_change_callback = callback
    
    def create_responsive_canvas(self, parent, width=400, height=500, **kwargs):
        """
        สร้าง Canvas ที่ปรับขนาดตาม DPI scaling อัตโนมัติ
        
        Returns:
            canvas: Canvas object พร้อมเมธอดเพิ่มเติม
        """
        canvas = tk.Canvas(parent, width=width, height=height, **kwargs)
        
        # เก็บขนาดเริ่มต้น
        canvas._original_width = width
        canvas._original_height = height
        canvas._canvas_items = {}  # เก็บ items ที่สร้างใน canvas
        
        # Override create_window เพื่อเก็บตำแหน่งเริ่มต้น
        original_create_window = canvas.create_window
        def responsive_create_window(x, y, window=None, **create_kwargs):
            item_id = original_create_window(x, y, window=window, **create_kwargs)
            # เก็บตำแหน่งเริ่มต้นไว้
            canvas._canvas_items[item_id] = {
                'type': 'window',
                'original_x': x,
                'original_y': y,
                'widget': window
            }
            return item_id
        canvas.create_window = responsive_create_window
        
        # เพิ่มเมธอดสำหรับปรับขนาด
        def resize_canvas(scaling_factor):
            new_width = int(canvas._original_width * scaling_factor)
            new_height = int(canvas._original_height * scaling_factor)
            canvas.config(width=new_width, height=new_height)
            
            # ปรับตำแหน่ง items ใน canvas
            for item_id, item_info in canvas._canvas_items.items():
                if item_info['type'] == 'window':
                    new_x = int(item_info['original_x'] * scaling_factor)
                    new_y = int(item_info['original_y'] * scaling_factor)
                    canvas.coords(item_id, new_x, new_y)
        
        canvas.resize_canvas = resize_canvas
        return canvas
    
    def register_canvas_for_scaling(self, canvas, original_width=None, original_height=None):
        """
        ลงทะเบียน Canvas ที่มีอยู่แล้วให้ปรับขนาดตาม DPI scaling
        
        Args:
            canvas: Canvas object ที่มีอยู่แล้ว
            original_width: ความกว้างเริ่มต้น (ถ้าไม่ระบุจะใช้ขนาดปัจจุบัน)
            original_height: ความสูงเริ่มต้น (ถ้าไม่ระบุจะใช้ขนาดปัจจุบัน)
        """
        if original_width is None:
            original_width = canvas.winfo_reqwidth()
        if original_height is None:
            original_height = canvas.winfo_reqheight()
            
        canvas._original_width = original_width
        canvas._original_height = original_height
        canvas._canvas_items = {}
        
        # เก็บ reference ไว้สำหรับปรับขนาดทีหลัง
        if not hasattr(self, '_registered_canvases'):
            self._registered_canvases = []
        self._registered_canvases.append(canvas)
        
        # เพิ่มเมธอดสำหรับปรับขนาด
        def resize_canvas(scaling_factor):
            new_width = int(canvas._original_width * scaling_factor)
            new_height = int(canvas._original_height * scaling_factor)
            canvas.config(width=new_width, height=new_height)
            
            # ปรับตำแหน่ง items ใน canvas
            for item_id, item_info in canvas._canvas_items.items():
                if item_info['type'] == 'window':
                    new_x = int(item_info['original_x'] * scaling_factor)
                    new_y = int(item_info['original_y'] * scaling_factor)
                    canvas.coords(item_id, new_x, new_y)
        
        canvas.resize_canvas = resize_canvas
        
        # Override create_window เพื่อเก็บตำแหน่งเริ่มต้น
        if not hasattr(canvas, '_original_create_window'):
            canvas._original_create_window = canvas.create_window
            
            def responsive_create_window(x, y, window=None, **create_kwargs):
                item_id = canvas._original_create_window(x, y, window=window, **create_kwargs)
                # เก็บตำแหน่งเริ่มต้นไว้
                canvas._canvas_items[item_id] = {
                    'type': 'window',
                    'original_x': x,
                    'original_y': y,
                    'widget': window
                }
                return item_id
            canvas.create_window = responsive_create_window
    
    def get_current_dpi(self, root):
        """ดึงค่า DPI ปัจจุบัน"""
        return self._get_window_dpi(root)
    
    def get_scaling_factor(self, root):
        """ดึงค่า scaling factor ปัจจุบัน"""
        dpi = self._get_window_dpi(root)
        return self._calculate_optimal_scaling(dpi)


# ฟังก์ชันสำหรับใช้งานแบบง่าย
def setup_dpi_awareness(mode="system_aware"):
    """ฟังก์ชันสำหรับตั้งค่า DPI awareness แบบง่าย"""
    dpi_manager = DpiManager()
    dpi_manager.setup_dpi_awareness(mode)
    return dpi_manager

def make_window_dpi_aware(root, dpi_manager=None):
    """ทำให้หน้าต่างรองรับ DPI แบบง่าย"""
    if dpi_manager is None:
        dpi_manager = DpiManager()
        dpi_manager.setup_dpi_awareness()
    
    dpi_manager.make_dpi_aware(root)
    return dpi_manager


# เก็บ reference ของ class หลักไว้ก่อน
_DpiManagerCore = DpiManager

# Backward compatibility wrapper (สำหรับโค้ดเก่า)
class DpiManagerLegacy:
    """Legacy wrapper สำหรับโค้ดเก่าที่ใช้ interface เดิม"""
    
    def __init__(self):
        self._manager = _DpiManagerCore()
    
    def enable_win_dpi_awareness(self, mode="system"):
        mode_map = {"system": "system_aware", "permonitor": "per_monitor_aware"}
        self._manager.setup_dpi_awareness(mode_map.get(mode, "system_aware"))
    
    def bind_auto_update(self, root):
        self._manager.make_dpi_aware(root)
    
    def set_monitor_change_callback(self, callback):
        self._manager.set_monitor_change_callback(callback)
    
    def _get_window_dpi(self, root):
        return self._manager.get_current_dpi(root)
    
    def register_canvas_for_scaling(self, canvas, original_width=None, original_height=None):
        """ลงทะเบียน Canvas ให้ปรับขนาดตาม DPI scaling (Legacy wrapper)"""
        return self._manager.register_canvas_for_scaling(canvas, original_width, original_height)


# สำหรับ backward compatibility - ใช้ legacy wrapper เป็น default
DpiManager = DpiManagerLegacy

# Export ทั้ง new และ legacy interface
DpiManagerNew = _DpiManagerCore