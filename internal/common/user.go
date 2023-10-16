package common

type Username string

type User struct {
	Username Username `json:"username"`
	Debts    []struct {
		Username Username `json:"username"`
		Amount   float32  `json:"amount"`
	}
}
