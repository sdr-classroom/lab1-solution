package server

import (
	"encoding/gob"
	"fmt"
	"log"
	"net"
	"reflect"

	"github.com/olivierlmr/SDR23F/lab1/internal/common"
	"github.com/olivierlmr/SDR23F/lab1/internal/messages"
)

/*
LOW-LEVEL SERVER LOGIC
Handles connections and such
*/

/*
- `sartServer` function, which
	- Launches tcp/server goroutine
	- Launches goroutine for message handling: receives input from tcp/server goroutine, calls the correct API on manifs, formats results into a message, and send it back.
*/

func parseConfig(config Config) Graph {
	graph := make(Graph)
	for _, user := range config.Users {
		graph[user.Username] = make(Debts)
		for _, debt := range user.Debts {
			graph[user.Username][debt.Username] = debt.Amount
		}
	}
	graph.SimplifyGraph()
	return graph
}

func StartServer(config Config) {
	listener, err := net.Listen("tcp", fmt.Sprintf("localhost:%d", config.Port))
	if err != nil {
		log.Fatal(err)
	}

	common.ConfigGlobalLogger(config.Debug)

	debts := parseConfig(config)

	requestsChan := make(chan request)

	go handleRequests(requestsChan, debts)

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Print(err)
		} else {
			go handleConn(conn, requestsChan)
		}
	}
}

func handleConn(conn net.Conn, requestHandlerChan chan request) {
	defer conn.Close()

	logger := common.GetGlobalLogger()

	responses := make(chan messages.Message)

	who := conn.RemoteAddr().String()
	logger.Info("New connection:", who)

	messages.RegisterMessages()

	encoder := gob.NewEncoder(conn)
	decoder := gob.NewDecoder(conn)

	for {
		var msg messages.Message
		err := decoder.Decode(&msg)
		if err != nil {
			logger.Error("Error in decoding message ", err)
			break
		}

		logger.Info("Received a message : ", msg, reflect.TypeOf(msg))

		requestHandlerChan <- request{message: msg, responseChan: responses}

		msg = <-responses

		logger.Info("Sending response back to client:", msg, reflect.TypeOf(msg))
		err = encoder.Encode(&msg)
		if err != nil {
			logger.Fatal("Failure in encoding message", msg, err)
		}
	}
}

type request struct {
	message      messages.Message
	responseChan chan messages.Message
}

func handleRequests(requests chan request, graph Graph) {
	//logger := common.GetGlobalLogger()

	for req := range requests {
		switch req.message.(type) {
		case messages.GetRequest:
			request := req.message.(messages.GetRequest)
			switch req.message.(messages.GetRequest).GetType {
			case messages.Debts:
				msg := messages.GetResponse{Debts: graph.GetDebts(request.Username)}
				req.responseChan <- msg
			case messages.Credits:
				req.responseChan <- messages.GetResponse{Debts: graph.GetCredits(request.Username)}
			}
		case messages.PayRequest:
			request := req.message.(messages.PayRequest)
			graph.Pay(request.Source, request.Receivers, request.Amount)
			req.responseChan <- messages.PayResponse{Success: true}
		default:
			req.responseChan <- messages.ErrorResponse{Message: "Unknown request type : " + reflect.TypeOf(req.message).String()}
		}
	}
}
