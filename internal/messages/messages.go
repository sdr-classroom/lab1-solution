package messages

import "encoding/gob"

type Message interface{}

func RegisterMessages() {
	gob.Register(GetRequest{})
	gob.Register(GetResponse{})
	gob.Register(ErrorResponse{})
	gob.Register(PayRequest{})
	gob.Register(PayResponse{})
}
