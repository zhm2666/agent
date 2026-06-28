package bus

import (
	"context"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
	"time"
)

type Bus interface {
	Sum(ctx context.Context, a, b int) int
	Product(ctx context.Context, a, b int) int
}

type bus struct {
	tracer trace.Tracer
}

func NewBus(tracer trace.Tracer) Bus {
	return &bus{
		tracer: tracer,
	}
}

func (bus *bus) Sum(ctx context.Context, a, b int) int {
	_, span := bus.tracer.Start(ctx, "sum", trace.WithAttributes(attribute.Int("a", a), attribute.Int("b", b)))
	defer span.End()
	c := a + b
	span.SetAttributes(attribute.Int("c", c))
	<-time.After(time.Millisecond * 100)
	return c
}
func (bus *bus) Product(ctx context.Context, a, b int) int {
	_, span := bus.tracer.Start(ctx, "product", trace.WithAttributes(attribute.Int("a", a), attribute.Int("b", b)))
	defer span.End()
	c := a * b
	<-time.After(time.Millisecond * 200)
	return c
}
