package logging

import (
	"os"
	"path/filepath"
	"sync"

	"go.uber.org/zap"
)

var (
	_globalLogger *zap.Logger
	_once         sync.Once
	_logRootDir   string
)

// Init 初始化日志系统
func Init() error {
	var err error
	_once.Do(func() {
		// 获取项目根目录
		execPath, _ := os.Executable()
		projectRoot := filepath.Dir(execPath)
		if projectRoot == "" {
			projectRoot = "."
		}

		_logRootDir = filepath.Join(projectRoot, "logs")
		if err = os.MkdirAll(_logRootDir, 0755); err != nil {
			return
		}

		// 配置zap
		config := zap.Config{
			Level:            zap.NewAtomicLevelAt(zap.DebugLevel),
			Development:       false,
			Encoding:          "json",
			EncoderConfig:     zap.NewProductionEncoderConfig(),
			OutputPaths:       []string{"stdout", filepath.Join(_logRootDir, "app.log")},
			ErrorOutputPaths: []string{"stderr", filepath.Join(_logRootDir, "error.log")},
		}

		_globalLogger, err = config.Build()
	})

	return err
}

// GetLogger 获取指定名称的logger
func GetLogger(name string) *zap.Logger {
	if _globalLogger == nil {
		Init()
	}
	return _globalLogger.Named(name)
}

// GetRootDir 获取日志目录
func GetRootDir() string {
	return _logRootDir
}

// Sync 刷新日志
func Sync() {
	if _globalLogger != nil {
		_globalLogger.Sync()
	}
}
