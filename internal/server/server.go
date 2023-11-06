package server

import (
	"encoding/gob"
	"fmt"
	"log"
	"net"
	"reflect"

	"debtManager/internal/common"
	"debtManager/internal/messages"
)

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
			if err.Error() == "EOF" {
				logger.Info("Connection closed by client:", who)
				break
			}
			logger.Error("Error in decoding message ", err)
			continue
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
	logger := common.GetGlobalLogger()

	logger.Info("Starting request handler")

	for req := range requests {
		logger.Info("Handling request", req.message, reflect.TypeOf(req.message))
		switch req.message.(type) {
		case messages.GetRequest:
			request := req.message.(messages.GetRequest)
			username := request.Username
			if _, ok := graph[username]; !ok {
				req.responseChan <- messages.ErrorResponse{Message: "User " + string(username) + " not found"}
				continue
			}
			switch req.message.(messages.GetRequest).GetType {
			case messages.Debts:
				msg := messages.GetResponse{Debts: graph.GetDebts(request.Username)}
				req.responseChan <- msg
			case messages.Credits:
				req.responseChan <- messages.GetResponse{Debts: graph.GetCredits(request.Username)}
			}
		case messages.PayRequest:
			request := req.message.(messages.PayRequest)
			err := graph.Pay(request.Source, request.Receivers, request.Amount)
			if err != nil {
				req.responseChan <- messages.ErrorResponse{Message: err.Error()}
				continue
			}
			req.responseChan <- messages.PayResponse{Success: true}
		default:
			req.responseChan <- messages.ErrorResponse{Message: "Unknown request type : " + reflect.TypeOf(req.message).String()}
		}
	}
}
