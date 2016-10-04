package main

import (
	"flag"
	"fmt"
	"io"
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

func (cc *ConnectionCount) stats() (int, int) {
	cc.mu.Lock()
	defer cc.mu.Unlock()

	return cc.max_conn, cc.total_conn
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

	time.Sleep(3 * time.Second)
	http.SetCookie(w, &sess_cookie)
	io.WriteString(w, resp)
}

func stats_handler(w http.ResponseWriter, r *http.Request) {
	http.SetCookie(w, &sess_cookie)
	max_conn, total_conn := scoreboard.stats()
	fmt.Fprintf(w, "max_conn=%d\ntotal_conn=%d\n", max_conn, total_conn)
}

func main() {
	portPtr := flag.Int("port", 8080, "TCP port to listen on")
	idPtr := flag.Int("id", 1, "Server ID")

	flag.Parse()

	resp = fmt.Sprintf("server%d", *idPtr)
	sess_cookie.Name = "JESSIONID"
	sess_cookie.Value = fmt.Sprintf("%d", *idPtr)

	http.HandleFunc("/", root_handler)
	http.HandleFunc("/slow", slow_handler)
	http.HandleFunc("/stats", stats_handler)
	portStr := fmt.Sprintf(":%d", *portPtr)
	http.ListenAndServe(portStr, nil)
}
