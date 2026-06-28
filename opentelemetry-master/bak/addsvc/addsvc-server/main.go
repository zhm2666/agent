package main

import (
	"addsvc/addsvc-server/server"
	"addsvc/proto"
	"google.golang.org/grpc"
	"log"
	"net"
)

func main() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatal(err)
	}
	s := grpc.NewServer()
	proto.RegisterAddServer(s, server.NewAddSvc())
	if err := s.Serve(lis); err != nil {
		log.Fatal(err)
	}
}
