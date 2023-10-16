package main

import (
	"os"

	"github.com/olivierlmr/SDR23F/lab1/internal/client"
	"github.com/olivierlmr/SDR23F/lab1/internal/common"
)

func main() {
	username := os.Args[1]
	port := os.Args[2]

	client.StartClient(common.Username(username), port)
}
