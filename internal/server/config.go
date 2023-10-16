package server

import "github.com/olivierlmr/SDR23F/lab1/internal/common"

type Config struct {
	Debug bool          `json:"debug"`
	Port  uint16        `json:"port"`
	Users []common.User `json:"users"`
}
