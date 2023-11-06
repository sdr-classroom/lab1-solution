package messages

import "debtManager/internal/common"

// A GetType enum for getting the different types of messages (debts or credits)
type GetType int

const (
	Debts GetType = iota
	Credits
)

type GetRequest struct {
	GetType  GetType
	Username common.Username
}

type GetResponse struct {
	Debts map[common.Username]float32
}
