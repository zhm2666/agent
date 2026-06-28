package server

import (
	"addsvc/addsvc-server/bus"
	"addsvc/proto"
	"context"
)

type addSvc struct {
	proto.UnimplementedAddServer
}

func NewAddSvc() proto.AddServer {
	return &addSvc{}
}

func (s *addSvc) Sum(ctx context.Context, in *proto.SumRequest) (*proto.SumReply, error) {
	c := bus.Sum(in.A, in.B)
	return &proto.SumReply{
		V: c,
	}, nil
}
func (s *addSvc) Concat(ctx context.Context, in *proto.ConcatRequest) (*proto.ConcatReply, error) {
	c := bus.Concat(in.A, in.B)
	return &proto.ConcatReply{
		V: c,
	}, nil
}
