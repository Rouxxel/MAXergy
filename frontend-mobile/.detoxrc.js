/** @type {Detox.DetoxConfig} */
module.exports = {
  testRunner: {
    args: {
      '$0': 'jest',
      config: 'e2e/jest.config.js'
    },
    jest: {
      setupTimeout: 120000
    }
  },
  apps: {
    'ios.sim': {
      type: 'ios.app',
      binaryPath: 'bin/Exponent.app',
      build: 'echo \'You can build and run Expo apps with "npx expo start"\', then point Detox to it with a launch URL',
    },
    'android.emu': {
      type: 'android.apk',
      binaryPath: 'bin/Exponent.apk',
      build: 'echo \'You can build and run Expo apps with "npx expo start"\', then point Detox to it with a launch URL',
      reversePorts: [
        8081,
        19000,
        19001,
        19002
      ]
    }
  },
  devices: {
    simulator: {
      type: 'ios.simulator',
      device: {
        type: 'iPhone 15'
      }
    },
    emulator: {
      type: 'android.emulator',
      device: {
        avdName: 'Pixel_3a_API_30_x86'
      }
    }
  },
  configurations: {
    'ios.sim': {
      device: 'simulator',
      app: 'ios.sim'
    },
    'android.emu': {
      device: 'emulator',
      app: 'android.emu'
    }
  }
};
