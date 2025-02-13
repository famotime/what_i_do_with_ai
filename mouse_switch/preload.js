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

// 更新界面状态
function updateState() {
  getCurrentMouseState((state) => {
    if (document.getElementById('currentState')) {
      document.getElementById('currentState').textContent = state;
    }
  });
}

// 获取配置
function getConfig() {
  const doc = utools.db.get('mouse_switch_config');
  return doc ? doc.data : { autoSwitch: false };
}

// 保存配置
function saveConfig(config) {
  const doc = utools.db.get('mouse_switch_config');
  if (doc) {
    utools.db.put({
      _id: 'mouse_switch_config',
      data: config,
      _rev: doc._rev
    });
  } else {
    utools.db.put({
      _id: 'mouse_switch_config',
      data: config
    });
  }
}

// 初始化配置
function initConfig() {
  if (!utools.db.get('mouse_switch_config')) {
    saveConfig({ autoSwitch: false });
  }
}

window.exports = {
  "switch_mouse": {
    mode: "none",
    args: {
      // 设置配置
      setConfig: (config) => {
        saveConfig(config);
      },
      // 获取配置
      getConfig: () => {
        return getConfig();
      },
      enter: (action) => {
        // 初始化配置
        initConfig();

        // 获取配置
        const config = getConfig();
        const autoSwitch = config.autoSwitch;

        if (autoSwitch) {
          // 如果设置为自动切换，直接执行切换
          switchMouseButtons((state) => {
            if (document.getElementById('currentState')) {
              document.getElementById('currentState').textContent = state;
            }
          });
        } else {
          // 否则只显示当前状态
          updateState();
        }

        // 更新按钮显示状态
        const switchButton = document.getElementById('switchButton');
        if (switchButton) {
          switchButton.style.display = autoSwitch ? 'none' : 'block';
        }

        // 更新配置提示显示
        const configTip = document.getElementById('configTip');
        if (configTip) {
          configTip.textContent = autoSwitch ?
            '提示：当前为自动切换模式，可在设置中关闭' :
            '提示：可在设置中开启"自动切换"功能';
        }
      },
      switchMouse: switchMouseButtons
    }
  }
}