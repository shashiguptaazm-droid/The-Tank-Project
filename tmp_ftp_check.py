from ftplib import FTP, parse229, parse227

HOST = "ftp.medigyaan.xyz"
USER = "Owner@medigyaan.xyz"
PASS = "MeriMaa007"


class CustomFTP(FTP):
    def makepasv(self):
        try:
            resp = self.sendcmd("EPSV")
            host, port = parse229(resp, self.sock.getpeername())
            return host, port
        except Exception:
            resp = self.sendcmd("PASV")
            if resp.startswith("229"):
                host, port = parse229(resp, self.sock.getpeername())
            else:
                host, port = parse227(resp)
            return host, port


def parse_entries(entries):
    items = []
    for e in entries:
        parts = e.split(";")
        if len(parts) < 2:
            continue
        facts = {}
        for p in parts[:-1]:
            if "=" in p:
                k, v = p.split("=", 1)
                facts[k] = v
        name = parts[-1].strip()
        if not name or name in (".", ".."):
            continue
        items.append((facts.get("type", "file"), name, facts.get("size", "?"), facts.get("modify", "?")))
    return items


def ls(ftp, path):
    out = []
    try:
        ftp.retrlines("MLSD " + path, out.append)
        return parse_entries(out)
    except Exception:
        return None  # dir may not exist


KEY = ["searchv2.php", "getQuestions.php", "get_single_question.php",
       "getTopics.php", "getuserquizzes.php", "submitAnswerx1.php",
       "update_question_topic.php", "update_question_explanation.php",
       "generate_questions_ai.php", "messenger_api.php", "ai_training_log.php",
       "thesis_topics_search.php", "ask_ai2.php", "api_key.php", "model_rotator.php",
       "zz_topic_batch.php", "zz_topic_save.php", "zz_repair_eopts.php",
       "zz_add_option_e.php", "livebattle.php", "join_lobby.php"]

ftp = CustomFTP()
ftp.connect(HOST, 21, timeout=30)
ftp.login(USER, PASS)
ftp.set_pasv(True)

for d in ["/api", "/Neurons", "/Neurons/api", "/public_html"]:
    items = ls(ftp, d)
    if items is None:
        print("\n=== %s : (no such dir / listing failed) ===" % d)
        continue
    php = sorted([i for i in items if i[0] == "file" and i[1].endswith(".php")])
    subdirs = [i[1] for i in items if i[0] == "dir"]
    print("\n=== %s : %d php, %d subdirs ===" % (d, len(php), len(subdirs)))
    print("subdirs:", ", ".join(subdirs[:30]))
    byname = {i[1]: i for i in php}
    for name in KEY:
        if name in byname:
            t, n, s, m = byname[name]
            print("  OK   %-32s %10s bytes  %s" % (name, s, m))
        else:
            print("  --   %-32s (not present)" % name)

ftp.quit()
print("\nDONE")
