"""An example of a simple HTTP server."""
import json
import mimetypes
import pickle
import socket
from os.path import isdir
from urllib.parse import unquote_plus

# Pickle file for storing data
PICKLE_DB = "db.pkl"

# Directory containing www data
WWW_DATA = "www-data"

# Header template for a successful HTTP request
HEADER_RESPONSE_200 = """HTTP/1.1 200 OK\r
content-type: %s\r
content-length: %d\r
connection: Close\r
\r
"""

# Represents a table row that holds user data
TABLE_ROW = """
<tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
</tr>
"""

# Template for a 404 (Not found) error
RESPONSE_404 = """HTTP/1.1 404 Not found\r
content-type: text/html\r
connection: Close\r
\r
<!doctype html>
<h1>404 Page not found</h1>
<p>Page cannot be found.</p>
"""

RESPONSE_301 = """HTTP/1.1 301 Moved Permanently\r
location: %s\r
connection: Close\r
\r
"""

RESPONSE_400 = """HTTP/1.1 400 Bad Request\r
content-type: text/html\r
connection: Close\r
\r
<!doctype html>
<h1>400 Bad Request</h1>
<p>Page cannot be found.</p>
"""

RESPONSE_405 = """HTTP/1.1 405 Method Not Allowed\r
content-type: text/html\r
connection: Close\r
\r
<!doctype html>
<h1>405 Page Not Allowed</h1>
<p>Method Not Allowed.</p>
"""


def save_to_db(first, last):
    """Create a new user with given first and last name and store it into
    file-based database.

    For instance, save_to_db("Mick", "Jagger"), will create a new user
    "Mick Jagger" and also assign him a unique number.

    Do not modify this method."""

    existing = read_from_db()
    existing.append({
        "number": 1 if len(existing) == 0 else existing[-1]["number"] + 1,
        "first": first,
        "last": last
    })
    with open(PICKLE_DB, "wb") as handle:
        pickle.dump(existing, handle)


def read_from_db(criteria=None):
    """Read entries from the file-based DB subject to provided criteria

    Use this method to get users from the DB. The criteria parameters should
    either be omitted (returns all users) or be a dict that represents a query
    filter. For instance:
    - read_from_db({"number": 1}) will return a list of users with number 1
    - read_from_db({"first": "bob"}) will return a list of users whose first
    name is "bob".

    Do not modify this method."""
    if criteria is None:
        criteria = {}
    else:
        # remove empty criteria values
        for key in ("number", "first", "last"):
            if key in criteria and criteria[key] == "":
                del criteria[key]

        # cast number to int
        if "number" in criteria:
            criteria["number"] = int(criteria["number"])

    try:
        with open(PICKLE_DB, "rb") as handle:
            data = pickle.load(handle)

        filtered = []
        for entry in data:
            predicate = True

            for key, val in criteria.items():
                if val != entry[key]:
                    predicate = False

            if predicate:
                filtered.append(entry)

        return filtered
    except (IOError, EOFError):
        return []


def parse_headers(client):
    headers = dict()
    while True:
        line = client.readline().decode("utf-8").strip()
        if not line:
            return headers
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()


def parse_get_parametars(p):
    if p == "":
        return None
    d = dict()
    parametars = p.split("&")
    for i in parametars:
        key, value = i.split("=", 1)
        d[key.strip()] = value.strip()
    return d


def process_request(connection, address):
    client = connection.makefile("wrb")
    line = client.readline().decode("utf-8").strip()

    try:
        method, uri, version = line.split(" ")
        headers = parse_headers(client)
        get_parameters = ""

        if method != "GET" and method != "POST":
            print("405 Error : Wrong Method")
            client.write(RESPONSE_405.encode("utf-8"))
            client.close()

        if uri[0] != "/" and not (len(uri) > 0):
            print("400 Error : Bad Request")
            client.write(RESPONSE_400.encode("utf-8"))
            client.close()

        if version != "HTTP/1.1":
            print("400 Error : Bad Request")
            client.write(RESPONSE_400.encode("utf-8"))
            client.close()

        if "host" not in headers.keys():
            print("400 Error : Bad Request")
            client.write(RESPONSE_400.encode("utf-8"))
            client.close()

        if method == "POST" and "content-length" not in headers.keys():
            print("400 Error : Bad Request, no Content-Length")
            client.write(RESPONSE_400.encode("utf-8"))
            client.close()

        if "?" in uri:
            uri, get_parameters = uri.split("?", 1)

    except Exception as e:
        print("[%s:] Exception parsing '%s': %s" % (address, line, e))
        client.write(RESPONSE_400.encode("utf-8"))
        client.close()

    uri_dynamic = ["/www-data/app-add", "/app-add", "/www-data/app-index", "/app-index", "/www-data/app-json", "/app-json"]
    dynamic = 0

    if uri in uri_dynamic:
        if uri == "/app-index" or uri == "/www-data/app-index":
            uri = "/app_list.html"
            dynamic = 1
            if method != "GET":
                print("405 Error : Wrong Method")
                client.write(RESPONSE_405.encode("utf-8"))
                client.close()

        elif uri == "/app-add" or uri == "/www-data/app-add":
            uri = "/app_add.html"
            dynamic = 2
            if method != "POST":
                print("405 Error : Wrong Method")
                client.write(RESPONSE_405.encode("utf-8"))
                client.close()

        elif uri == "/app-json" or "/www-data/app-json":
            dynamic = 3
            if method != "GET":
                print("405 Error : Wrong Method")
                client.write(RESPONSE_405.encode("utf-8"))
                client.close()
            try:
                get_parameters = unquote_plus(get_parameters, "utf-8")
                body = json.dumps(read_from_db(parse_get_parametars(get_parameters))).encode()
                head = HEADER_RESPONSE_200 % (
                    "application/json",
                    len(body)
                )
                client.write(head.encode("utf-8"))
                client.write(body)

            except Exception as e:
                print("[%s:] Exception parsing '%s': %s" % (address, line, e))
                client.write(RESPONSE_400.encode("utf-8"))
                client.close()

    if (uri[-1] == "/"):
        r_301 = RESPONSE_301 % ("http://" + headers["host"].split(":")[0] + ":" + headers["host"].split(":")[1] + uri + "index.html")
        uri += "index.html"
        client.write(r_301.encode("utf-8"))
    elif uri[-1] != "/" and "." not in uri:  # if doesnt have trailing slash and if its a dicitonary
        if (isdir(WWW_DATA + uri)):
            r_301 = RESPONSE_301 % ("http://" + headers["host"].split(":")[0] + ":" + headers["host"].split(":")[1] + uri + "/index.html")
            uri += "/index.html"
            client.write(r_301.encode("utf-8"))

    if dynamic in [0, 1, 2]:
        try:
            with open(WWW_DATA + "/" + uri, "rb") as handle:  # 200 ok
                body = handle.read()

            mime_type, _ = mimetypes.guess_type(WWW_DATA + "/" + uri)
            if mime_type == None:
                mime_type = "application/octet-stream"

            if dynamic == 0:
                head = HEADER_RESPONSE_200 % (
                    mime_type,
                    len(body)
                )
                client.write(head.encode("utf-8"))
                client.write(body)
            elif dynamic == 1:
                table = ""
                get_parameters = unquote_plus(get_parameters, "utf-8")
                students = read_from_db(parse_get_parametars(get_parameters))
                for student in students:
                    table += TABLE_ROW % (
                        student["number"],
                        student["first"],
                        student["last"],
                    )

                body = body.replace(b"{{students}}", table.encode("utf-8"))

                head = HEADER_RESPONSE_200 % (
                    mime_type,
                    len(body)
                )
                client.write(head.encode("utf-8"))
                client.write(body)
            elif dynamic == 2:
                post_parameters = (client.read(int(headers["content-length"])))
                post_parameters = unquote_plus(post_parameters.decode("utf-8"), "utf-8")
                d = parse_get_parametars(post_parameters)

                if "first" not in d.keys() and "last" not in d.keys():
                    print("400 Error : Bad Request, missing parameters")
                    client.write(RESPONSE_400.encode("utf-8"))
                    connection.close()

                save_to_db(str(d["first"]), str(d["last"]))
                head = HEADER_RESPONSE_200 % (
                    mime_type,
                    len(body)
                )
                client.write(head.encode("utf-8"))
                client.write(body)

        except IOError:
            client.write(RESPONSE_404.encode("utf-8"))
            client.close()

        finally:
            client.close()

    client.close()


def main(port):
    """Starts the server and waits for connections."""

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("", port))
    server.listen(1)

    print("Listening on %d" % port)

    while True:
        connection, address = server.accept()
        print("[%s:%d] CONNECTED" % address)
        process_request(connection, address)
        connection.close()
        print("[%s:%d] DISCONNECTED" % address)


if __name__ == "__main__":
    main(8080)
