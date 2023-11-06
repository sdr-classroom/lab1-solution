package main

import (
	"os"

	"debtManager/internal/client"
	"debtManager/internal/common"
)

func main() {
	username := os.Args[1]
	port := os.Args[2]

	client.StartClient(common.Username(username), port)
}
