package server

import "debtManager/internal/common"

type Config struct {
	Debug bool          `json:"debug"`
	Port  uint16        `json:"port"`
	Users []common.User `json:"users"`
}
