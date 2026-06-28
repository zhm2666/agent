package bus

import (
	"context"
)

type Bus interface {
	Sum(ctx context.Context, a, b int64) int64
	Concat(ctx context.Context, a, b string) string
}

type bus struct {
}

func NewBus() Bus {
	return &bus{}
}

func (bus *bus) Sum(_ context.Context, a, b int64) int64 {
	return a + b
}

func (bus *bus) Concat(_ context.Context, a, b string) string {
	return a + b
}
