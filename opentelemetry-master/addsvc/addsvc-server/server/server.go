package server

import (
	"addsvc/addsvc-server/bus"
	"addsvc/proto"
	strProto "addsvc/services/strsvc/proto"
	"context"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/baggage"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc/metadata"
	"log"
)

type addSvc struct {
	proto.UnimplementedAddServer
	bus        bus.Bus
	tracer     trace.Tracer
	strClient  strProto.StrClient
	propagator propagation.TextMapPropagator
}

func NewAddSvc(bus bus.Bus, tracer trace.Tracer, strClient strProto.StrClient, propagator propagation.TextMapPropagator) proto.AddServer {
	return &addSvc{
		bus:        bus,
		tracer:     tracer,
		strClient:  strClient,
		propagator: propagator,
	}
}

func (s *addSvc) Sum(ctx context.Context, in *proto.SumRequest) (*proto.SumReply, error) {
	ctx, span := s.tracer.Start(ctx, "addsvc.Sum")
	defer span.End()

	md := &propagation.MapCarrier{}
	s.propagator.Inject(ctx, md)
	ctx = metadata.NewOutgoingContext(ctx, metadata.New(*md))

	c := s.bus.Sum(ctx, in.A, in.B)
	return &proto.SumReply{
		V: c,
	}, nil
}
func (s *addSvc) Concat(ctx context.Context, in *proto.ConcatRequest) (*proto.ConcatReply, error) {
	//向上下文附加自定义信息
	b := customBaggage()
	ctx = baggage.ContextWithBaggage(ctx, b)

	ctx, span := s.tracer.Start(ctx, "addsvc.Concat")
	defer span.End()

	md := &propagation.MapCarrier{}
	s.propagator.Inject(ctx, md)
	ctx = metadata.NewOutgoingContext(ctx, metadata.New(*md))

	c := s.bus.Concat(ctx, in.A, in.B)
	countIn := &strProto.CountRequest{
		Str: c,
	}
	countRes, err := s.strClient.Count(ctx, countIn)
	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}
	span.SetAttributes(attribute.Int64("str_len", countRes.V))

	uppercaseIn := &strProto.UppercaseRequest{
		Str: c,
	}
	uppercaseRes, err := s.strClient.Uppercase(ctx, uppercaseIn)
	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}
	span.SetAttributes(attribute.String("str_uppercase", uppercaseRes.V))

	return &proto.ConcatReply{
		V: uppercaseRes.V,
	}, nil
}

func customBaggage() baggage.Baggage {
	b, _ := baggage.New()
	//属性定义
	gender, err := baggage.NewKeyValueProperty("gender", "1")
	if err != nil {
		log.Println(err)
		return b
	}
	age, err := baggage.NewKeyValueProperty("age", "18")
	if err != nil {
		log.Println(err)
		return b
	}

	//字段定义
	author, err := baggage.NewMember("author", "nick", gender, age)
	if err != nil {
		log.Println(err)
		return b
	}
	org, err := baggage.NewMember("org", "0voice")
	if err != nil {
		log.Println(err)
		return b
	}
	b1, err := baggage.New(author, org)
	if err != nil {
		log.Println(err)
		return b
	}
	return b1

}
