const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

// 获取当前鼠标状态
function getCurrentMouseState(callback) {
  const script = `
    Add-Type -TypeDefinition @'
    using System;
    using System.Runtime.InteropServices;
    public class MouseSettings {
        [DllImport("user32.dll")]
        public static extern int GetSystemMetrics(int nIndex);
        private const int SM_SWAPBUTTON = 23;
        public static string GetState() {
            return GetSystemMetrics(SM_SWAPBUTTON) != 0 ? "左手模式" : "右手模式";
        }
    }
'@
    [MouseSettings]::GetState()
  `;

  const tempScriptPath = path.join(utools.getPath('temp'), 'get_mouse_state.ps1');
  fs.writeFileSync(tempScriptPath, script, { encoding: 'utf8' });

  exec('powershell -NoProfile -ExecutionPolicy Bypass -File "' + tempScriptPath + '"',
    { encoding: 'utf8' },
    (error, stdout, stderr) => {
      try {
        fs.unlinkSync(tempScriptPath);
      } catch (e) {}

      if (error) {
        callback('获取状态失败');
        return;
      }
      callback(stdout.trim());
    }
  );
}

// 切换鼠标按键
function switchMouseButtons(callback) {
  const script = `
    Add-Type -TypeDefinition @'
    using System;
    using System.Runtime.InteropServices;
    public class MouseSettings {
        [DllImport("user32.dll")]
        public static extern bool SwapMouseButton(bool bSwap);
        [DllImport("user32.dll")]
        public static extern int GetSystemMetrics(int nIndex);
        private const int SM_SWAPBUTTON = 23;

        public static void Switch() {
            bool currentState = GetSystemMetrics(SM_SWAPBUTTON) != 0;
            SwapMouseButton(!currentState);
        }
    }
'@
    [MouseSettings]::Switch()
  `;

  const tempScriptPath = path.join(utools.getPath('temp'), 'switch_mouse.ps1');
  fs.writeFileSync(tempScriptPath, script, { encoding: 'utf8' });

  exec('powershell -NoProfile -ExecutionPolicy Bypass -File "' + tempScriptPath + '"',
    { encoding: 'utf8' },
    (error, stdout, stderr) => {
      try {
        fs.unlinkSync(tempScriptPath);
      } catch (e) {}

      // 切换后等待一小段时间再获取状态
      setTimeout(() => {
        getCurrentMouseState((state) => {
          callback(state);
          utools.showNotification('鼠标按键已切换为：' + state);
        });
      }, 200);
    }
  );
}

// 修改index.html中的内容
window.exports = {
  "switch_mouse": {
    mode: "none",
    args: {
      enter: (action) => {
        getCurrentMouseState((state) => {
          if (document.getElementById('currentState')) {
            document.getElementById('currentState').textContent = state;
          }
        });
      },
      switchMouse: switchMouseButtons
    }
  }
}