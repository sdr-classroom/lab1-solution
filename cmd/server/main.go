package main

import (
	"encoding/json"
	"os"

	"github.com/olivierlmr/SDR23F/lab1/internal/server"
)

func main() {
	configFileName := os.Args[1]

	// Read config json file
	content, err := os.ReadFile(configFileName)
	if err != nil {
		panic(err)
	}

	var config server.Config
	err = json.Unmarshal(content, &config)
	if err != nil {
		panic(err)
	}

	server.StartServer(config)
}
