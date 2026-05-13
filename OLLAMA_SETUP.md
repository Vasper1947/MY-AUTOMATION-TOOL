# Ollama Setup for Network & Phone Access

## Quick Start (Desktop Only)
```powershell
# 1. Install Ollama from https://ollama.ai
# 2. Run Ollama service
ollama serve

# 3. In another terminal, pull vision model
ollama pull llava
```

## Network Access (PC + Phone)

### Step 1: Install Ollama
- Download from https://ollama.ai
- Install on Windows

### Step 2: Configure Ollama for Network Access

#### Option A: PowerShell (Recommended)
```powershell
# Set environment variable
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")

# Restart PowerShell/Terminal for changes to take effect

# Run Ollama
ollama serve
```

#### Option B: System Environment Variable (Windows Settings)
1. Open Settings → System → About
2. Click "Advanced system settings"
3. Environment Variables
4. New User Variable: `OLLAMA_HOST = 0.0.0.0:11434`
5. Restart Ollama

#### Option C: Batch File (run_ollama.bat)
```batch
@echo off
set OLLAMA_HOST=0.0.0.0:11434
ollama serve
pause
```

### Step 3: Pull Vision Model
```powershell
ollama pull llava
# This downloads ~5GB model for image analysis
```

### Step 4: Find Your Computer's IP Address
```powershell
# In PowerShell:
ipconfig

# Look for "IPv4 Address" in your network adapter
# Usually something like: 192.168.x.x or 10.0.x.x
```

### Step 5: Access from Phone
1. Connect phone to same WiFi network
2. Open browser on phone
3. Visit: `http://{YOUR_PC_IP}:11434`
   - Example: `http://192.168.1.100:11434`

The extraction script will auto-detect and display the network URL.

## Models Available

- **llava** (5GB) - Best for product images, detailed analysis
- **llava:13b** (8GB) - Even better quality, slower
- **llama2** (4GB) - Fast text processing
- **neural-chat** (4GB) - Good for descriptions

## Verify Setup
```powershell
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Response should show list of models
```

## Troubleshooting

### Ollama not accessible from phone
- Verify phone is on same WiFi as PC
- Check Windows Firewall:
  - Settings → Firewall & Network Protection
  - Allow Ollama (ollama.exe) through firewall
  - Or disable firewall on private network (less secure)
- Verify IP address is correct

### Model download fails
- Check internet speed
- Ensure at least 10GB free disk space
- Models download to: `C:\Users\{USER}\.ollama\models`

### Slow AI descriptions
- Your PC specs matter (GPU accelerates)
- Smaller models (llava) vs larger (llava:13b)
- Batch processing is fine - let it run overnight for 1000+ products

## Integration with Extraction Script

The script auto-detects:
1. Ollama on localhost (fastest)
2. Ollama on network IP (phone access)
3. Shows network URL for phone access

During extraction, when prompted:
```
🤖 DETECTING OLLAMA SERVICE...
   ✅ Ollama found at: http://localhost:11434
   📱 Phone access: http://192.168.1.100:11434
Generate AI descriptions for products? (y/n):
```

Respond `y` to enable AI product descriptions.
