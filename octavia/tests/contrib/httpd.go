package main

import (
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"sync"
	"time"
)

var sess_cookie http.Cookie
var resp string

type ConnectionCount struct {
	mu         sync.Mutex
	cur_conn   int
	max_conn   int
	total_conn int
	packets    int
}

var scoreboard ConnectionCount

func (cc *ConnectionCount) open() {
	cc.mu.Lock()
	defer cc.mu.Unlock()

	cc.cur_conn++
	cc.total_conn++
}

func (cc *ConnectionCount) close() {
	cc.mu.Lock()
	defer cc.mu.Unlock()

	if cc.cur_conn > cc.max_conn {
		cc.max_conn = cc.cur_conn
	}
	cc.cur_conn--
}

func (cc *ConnectionCount) stats() (int, int, int) {
	cc.mu.Lock()
	defer cc.mu.Unlock()

	return cc.max_conn, cc.total_conn, cc.packets
}

func (cc *ConnectionCount) inc() {
	cc.mu.Lock()
	defer cc.mu.Unlock()

	cc.packets++
}

func (cc *ConnectionCount) reset() {
	cc.mu.Lock()
	defer cc.mu.Unlock()

	cc.max_conn = 0
	cc.total_conn = 0
	cc.packets = 0
}

func root_handler(w http.ResponseWriter, r *http.Request) {
	scoreboard.open()
	defer scoreboard.close()

	http.SetCookie(w, &sess_cookie)
	io.WriteString(w, resp)
}

func slow_handler(w http.ResponseWriter, r *http.Request) {
	scoreboard.open()
	defer scoreboard.close()

	delay, err := time.ParseDuration(r.URL.Query().Get("delay"))
	if err != nil {
		delay = 3 * time.Second
	}

	time.Sleep(delay)
	http.SetCookie(w, &sess_cookie)
	io.WriteString(w, resp)
}

func stats_handler(w http.ResponseWriter, r *http.Request) {
	http.SetCookie(w, &sess_cookie)
	max_conn, total_conn, packets := scoreboard.stats()
	fmt.Fprintf(w, "max_conn=%d\ntotal_conn=%d\npackets=%d\n", max_conn, total_conn, packets)
}

func reset_handler(w http.ResponseWriter, r *http.Request) {
	http.SetCookie(w, &sess_cookie)
	scoreboard.reset()
	fmt.Fprintf(w, "reset\n")
}

func udp_handler(port *int) {
	ServerConn, _ := net.ListenUDP("udp", &net.UDPAddr{IP: []byte{0, 0, 0, 0}, Port: *port, Zone: ""})
	defer ServerConn.Close()
	buf := make([]byte, 1024)
	for {
		n, addr, _ := ServerConn.ReadFromUDP(buf)
		scoreboard.inc()
		fmt.Println("Received ", string(buf[0:n]), " from ", addr)
		ServerConn.WriteTo([]byte(resp), addr)
	}
}

func main() {
	portPtr := flag.Int("port", 8080, "TCP port to listen on")
	idPtr := flag.String("id", "1", "Server ID")
	udpPortPtr := flag.Int("udpPort", -1, "UDP port to listen on. If port <=0 UDP server won't start")

	flag.Parse()

	resp = fmt.Sprintf("%s", *idPtr)
	sess_cookie.Name = "JSESSIONID"
	sess_cookie.Value = *idPtr

	http.HandleFunc("/", root_handler)
	http.HandleFunc("/slow", slow_handler)
	http.HandleFunc("/stats", stats_handler)
	http.HandleFunc("/reset", reset_handler)
	portStr := fmt.Sprintf(":%d", *portPtr)
	if *udpPortPtr > 0 {
		// only start server if flag is set
		go udp_handler(udpPortPtr)
	}
	http.ListenAndServe(portStr, nil)
}
