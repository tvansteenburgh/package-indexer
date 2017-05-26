package main

import (
	"bufio"
	"fmt"
	"log"
	"net"
	"runtime"
	"strconv"
	"strings"
	"time"
)

//ResponseCode is the code returned by the sever as a response to our requests
type ResponseCode string

const (
	//OK code
	OK = "OK"

	//FAIL code
	FAIL = "FAIL"

	//ERROR code
	ERROR = "ERROR"

	//UNKNOWN code
	UNKNOWN = "UNKNOWN"
)

//PackageIndexerClient sends messages to a running server.
type PackageIndexerClient interface {
	Name() string
	Close() error
	Send(msg string) (ResponseCode, error)
}

// TCPPackageIndexerClient connects to the running server via TCP
type TCPPackageIndexerClient struct {
	name   string
	conn   net.Conn
	reader *bufio.Reader
	writer *bufio.Writer
}

//Name return this client's name.
func (client *TCPPackageIndexerClient) Name() string {
	return client.name
}

//Close closes the connection to the server.
func (client *TCPPackageIndexerClient) Close() error {
	log.Printf("%s disconnecting", client.Name())
	return client.conn.Close()
}

func goid() int {
	var buf [64]byte
	n := runtime.Stack(buf[:], false)
	idField := strings.Fields(strings.TrimPrefix(string(buf[:n]), "goroutine "))[0]
	id, err := strconv.Atoi(idField)
	if err != nil {
		panic(fmt.Sprintf("cannot get goroutine id: %v", err))
	}
	return id
}

//Send sends amessage to the server using its line-oriented protocol
func (client *TCPPackageIndexerClient) Send(msg string) (ResponseCode, error) {
	client.reader.Reset(client.conn)

	extendTimoutFor(client.conn)
	//_, err := fmt.Fprintln(client.conn, msg)
	_, err := client.writer.WriteString(fmt.Sprintf("%s\n", msg))
	client.writer.Flush()

	log.Printf("Send:%s:%d: %s", client.conn.LocalAddr().String(), goid(), msg)

	if err != nil {
		return UNKNOWN, fmt.Errorf("Error sending message to server: %v", err)
	}

	extendTimoutFor(client.conn)
	//responseMsgBytes, err := client.reader.ReadBytes('\n')
	var readBuf [32]byte
	n, err := client.conn.Read(readBuf[0:])

	if err != nil {
		return UNKNOWN, fmt.Errorf("Error reading response code from server: %v", err)
	}

	responseMsg := string(readBuf[0:n])
	log.Printf(
		"Recv:%s:%d: %s",
		client.conn.LocalAddr().String(), goid(), responseMsg)
	returnedString := strings.TrimRight(responseMsg, "\n")

	if returnedString == OK {
		return OK, nil
	}

	if returnedString == FAIL {
		return FAIL, nil
	}

	if returnedString == ERROR {
		return ERROR, nil
	}

	return UNKNOWN, fmt.Errorf("Error parsing message from server [%s]: %v", responseMsg, err)
}

// MakeTCPPackageIndexClient returns a new instance of the client
func MakeTCPPackageIndexClient(name string, port int) (PackageIndexerClient, error) {
	host := fmt.Sprintf("localhost:%d", port)
	log.Printf("%s connecting to [%s]", name, host)
	conn, err := net.Dial("tcp", host)

	if err != nil {
		return nil, fmt.Errorf("Failed to open connection to [%s]: %#v", host, err)
	}

	return &TCPPackageIndexerClient{
		name:   name,
		conn:   conn,
		reader: bufio.NewReader(conn),
		writer: bufio.NewWriter(conn),
	}, nil
}

func extendTimoutFor(conn net.Conn) {
	whenWillThisConnectionTimeout := time.Now().Add(time.Second * 10)
	conn.SetDeadline(whenWillThisConnectionTimeout)
}
