package messages

import "debtManager/internal/common"

type PayRequest struct {
	Source    common.Username
	Amount    float32
	Receivers []common.Username
}

type PayResponse struct {
	Success bool
}
