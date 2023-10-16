package messages

type ErrorResponse struct {
	Message string
}

func (m *ErrorResponse) String() string {
	return m.Message
}
