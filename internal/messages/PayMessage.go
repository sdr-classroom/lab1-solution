package messages

import "github.com/olivierlmr/SDR23F/lab1/internal/common"

type PayRequest struct {
	Source    common.Username
	Amount    float32
	Receivers []common.Username
}

type PayResponse struct {
	Success bool
}
