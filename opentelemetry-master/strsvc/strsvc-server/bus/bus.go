package bus

import (
	"context"
	"strings"
)

type Bus interface {
	Count(ctx context.Context, str string) int64
	Uppercase(ctx context.Context, str string) string
}

type bus struct {
}

func NewBus() Bus {
	return &bus{}
}

func (bus *bus) Count(_ context.Context, str string) int64 {
	return int64(len(str))
}

func (bus *bus) Uppercase(_ context.Context, str string) string {
	return strings.ToUpper(str)
}
