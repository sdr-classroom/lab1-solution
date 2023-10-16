package common

import "log"

var logger *Logger

type Logger struct {
	debugMode bool
}

func GetGlobalLogger() *Logger {
	if logger == nil {
		logger = newLogger(false)
	}
	return logger
}

func ConfigGlobalLogger(debugMode bool) {
	logger = GetGlobalLogger()
	logger.debugMode = debugMode
}

func newLogger(debugMode bool) *Logger {
	return &Logger{
		debugMode: debugMode,
	}
}

func (l *Logger) Info(args ...interface{}) {
	if l.debugMode {
		args = append([]interface{}{"[Info]"}, args...)
		log.Println(args...)
	}
}

func (l *Logger) Warning(args ...interface{}) {
	if l.debugMode {
		args = append([]interface{}{"[Warning]"}, args...)
		log.Println(args...)
	}
}

func (l *Logger) Error(args ...interface{}) {
	if l.debugMode {
		args = append([]interface{}{"[Error]"}, args...)
		log.Println(args...)
	}
}

func (l *Logger) Fatal(args ...interface{}) {
	args = append([]interface{}{"[Fatal]"}, args...)
	log.Fatalln(args...)
}
