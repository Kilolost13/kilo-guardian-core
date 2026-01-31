# 📷 Camera Setup Guide

## ✅ Camera Integration Complete!

Your Kilo AI Memory Assistant now has **full camera support** using your tablet's built-in camera!

---

## 🎯 How Camera Works

### **Tablet Camera (Recommended)**
- ✅ Uses **Galaxy Tab A7 Lite's built-in cameras**
- ✅ **Front camera** for selfies
- ✅ **Back camera** for scanning (prescriptions, receipts, etc.)
- ✅ **No PC cameras needed** - all processing on tablet

### **Architecture**
```
Galaxy Tab A7 Lite
    │
    ├─► Front Camera (8MP) ───┐
    ├─► Back Camera (8MP)  ───┼─► Browser Camera API
    │                          │
    └─► Browser ───────────────┴─► Captures Image
                                   │
                                   ▼
                            Upload to PC Backend
                                   │
                                   ▼
                            AI Processing (OCR, Analysis)
```

---

## 📱 Using the Camera on Your Tablet

### **Step 1: Grant Camera Permission**

When you first tap the 📷 camera button, your browser will ask:

```
"Allow http://192.168.68.64:3000 to use your camera?"
```

**Tap "Allow"** ✅

### **Step 2: Choose Which Camera**

The app automatically uses:
- **Back camera** (environment-facing) for scanning
- **Front camera** (user-facing) can be toggled

### **Step 3: Capture Image**

1. **Position** the item (prescription, receipt, document) in the frame
2. **Tap "📸 CAPTURE"** button
3. **Review** the captured image
4. **Tap "✓ USE THIS IMAGE"** to upload or "🔄 RETAKE" to try again

---

## 🎨 Camera Features

### **Built-in Features**
- ✅ **Live preview** - See what you're capturing in real-time
- ✅ **Frame guide** - Dashed border shows capture area
- ✅ **Image review** - Check before uploading
- ✅ **Retake option** - Easy to try again
- ✅ **Touch-optimized** - Large buttons for tablet

### **Smart Detection**
- 📋 **Prescription scanning** - OCR extracts medication info
- 🧾 **Receipt scanning** - Captures transaction details
- 📸 **General photos** - AI describes what it sees

---

## 📸 Where to Use Camera

### **1. Dashboard**
- Tap 📷 button next to chat input
- Capture general images
- AI will describe and remember them

### **2. Medications Page**
- Tap "📷 SCAN PRESCRIPTION"
- Captures medication label
- OCR extracts: name, dosage, instructions

### **3. Finance Page**
- Tap "📷 SCAN RECEIPT"
- Captures receipt
- Extracts: amount, date, items

---

## 🔐 Camera Permissions

### **How to Grant Permission**

**First Time:**
1. Tap 📷 camera button
2. Browser popup appears
3. Tap "Allow"

**If You Denied Permission:**
1. Open browser settings
2. Go to "Site Settings" or "Permissions"
3. Find http://192.168.68.64:3000
4. Change camera to "Allow"

### **Samsung Internet**
```
Menu (⋮) → Settings → Sites and downloads →
Site permissions → Camera → Allow
```

### **Chrome**
```
Menu (⋮) → Settings → Site settings →
Camera → Allow for http://192.168.68.64:3000
```

---

## 💡 Tips for Best Results

### **Prescription Scanning**
- ✅ Good lighting (natural light is best)
- ✅ Flat surface (avoid shadows)
- ✅ All text visible and in focus
- ✅ Hold steady when capturing

### **Receipt Scanning**
- ✅ Flatten the receipt
- ✅ Entire receipt in frame
- ✅ Avoid glare from lighting
- ✅ High contrast background

### **General Photos**
- ✅ Center the subject
- ✅ Good lighting
- ✅ Sharp focus
- ✅ Fill the frame

---

## 🐛 Troubleshooting

### **Camera Not Working?**

**Check Permissions:**
```
Settings → Apps → Browser → Permissions → Camera → Allow
```

**Browser Issues:**
- ✅ Use **Chrome** or **Samsung Internet** (best support)
- ✅ Avoid **Firefox** (may have permission issues)
- ❌ Don't use **Opera Mini** (no camera support)

### **"Camera Not Found" Error**

**Causes:**
1. Permission denied
2. Camera in use by another app
3. Browser doesn't support camera API

**Fix:**
1. Grant permission in browser
2. Close other camera apps
3. Refresh the page

### **Image Quality Issues**

**Blurry images:**
- Tap screen to focus before capturing
- Hold tablet steady
- Ensure good lighting

**Dark images:**
- Move to better lighting
- Clean camera lens
- Adjust angle to avoid shadows

---

## 🎯 Future: 4-Camera Appliance

Your future setup with **4 cameras on appliance + tablet**:

```
Standalone Appliance
    │
    ├─► Camera 1 (Front door)
    ├─► Camera 2 (Kitchen)
    ├─► Camera 3 (Bedroom)
    └─► Camera 4 (Office)
         │
         └─► All stream to AI for processing

Galaxy Tab A7 Lite
    │
    ├─► Accesses appliance via WiFi
    ├─► Uses own camera for scanning
    └─► Displays all camera feeds
```

**Current setup tests the tablet camera part!** ✅

---

## 📊 Technical Details

### **Camera Specifications**

**Galaxy Tab A7 Lite:**
- **Back Camera**: 8 MP, f/2.2
- **Front Camera**: 2 MP, f/2.4
- **Video**: 1080p@30fps
- **Supported**: WebRTC, MediaStream API

### **Browser Support**
- ✅ Chrome 53+
- ✅ Samsung Internet 5+
- ✅ Firefox 36+
- ✅ Edge 12+

### **Image Format**
- **Capture**: JPEG
- **Resolution**: 1280x720 (default)
- **Size**: ~100-300 KB per image
- **Upload**: Base64 or Blob

---

## 🎉 Ready to Test!

1. **Open**: http://192.168.68.64:3000 on your tablet
2. **Login**: to Dashboard
3. **Tap**: 📷 camera button
4. **Allow**: camera permission
5. **Capture**: test image
6. **Upload**: to AI for processing

**Your tablet camera is now fully integrated!** 📱✨

---

## 📝 Notes

- Camera only works on **HTTPS** or **localhost/local IP** (security requirement)
- Current URL (http://192.168.68.64:3000) works because it's **local network**
- Images are sent to PC backend for AI processing (OCR, description)
- No images stored permanently (privacy-first design)

---

**Ready to scan!** 📷🚀
