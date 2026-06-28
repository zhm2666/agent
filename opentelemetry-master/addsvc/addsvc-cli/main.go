package main

import (
	"addsvc/proto"
	"context"
	"fmt"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"log"
)

func main() {
	sum()
	concat()
}

func sum() {
	conn, err := grpc.Dial("localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()
	client := proto.NewAddClient(conn)
	ctx := context.Background()
	in := &proto.SumRequest{
		A: 11,
		B: 12,
	}
	res, err := client.Sum(ctx, in)
	if err != nil {
		log.Println(err)
		return
	}
	fmt.Println(res)
}
func concat() {
	conn, err := grpc.Dial("localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()
	client := proto.NewAddClient(conn)
	ctx := context.Background()
	in := &proto.ConcatRequest{
		A: "abcd",
		B: "efg",
	}
	res, err := client.Concat(ctx, in)
	if err != nil {
		log.Println(err)
		return
	}
	fmt.Println(res)
}
