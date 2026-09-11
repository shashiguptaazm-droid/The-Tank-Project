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

# --- 1) Patch getQuestions.php: auto-generate questions when a topic has none ---
gq = open("tmp_php/getQuestions.php", "r", encoding="utf-8", errors="replace").read()
old_empty = """    if (empty($all_ids)) {
        throw new Exception("No questions found for this topic.");
    }"""
new_empty = """    // No user goes empty handed: if a real topic has zero questions, ask the
    // AI module to generate a starter set, then re-run the id query.
    if (empty($all_ids) && $topic !== null && $topic !== '' && $subject !== 'BCBR') {
        require_once __DIR__ . '/generate_questions_ai.php';
        try {
            generateQuestionsForTopic($conn, $subject, $topic, 5);
            $id_stmt = $conn->prepare("SELECT question_id FROM questions WHERE subject = ? AND topic = ? ORDER BY question_id ASC");
            $id_stmt->bind_param("ss", $subject, $topic);
            $id_stmt->execute();
            $id_result = $id_stmt->get_result();
            $all_ids = [];
            while ($row = $id_result->fetch_assoc()) {
                $all_ids[] = intval($row['question_id']);
            }
            $id_stmt->close();
        } catch (Exception $genErr) {
            // Generation failed; fall through so the caller still sees the error below.
        }
    }

    if (empty($all_ids)) {
        throw new Exception("No questions found for this topic.");
    }"""
assert old_empty in gq, "getQuestions empty-branch pattern not found"
gq = gq.replace(old_empty, new_empty)
open("tmp_php/getQuestions.php", "w", encoding="utf-8").write(gq)
print("patched getQuestions.php")

# --- 2) Patch update_question_topic.php: allow overwriting placeholder/junk topics ---
ut = open("tmp_php/update_question_topic.php", "r", encoding="utf-8", errors="replace").read()
old_guard = """    // Only fill the topic when it is missing, so curated topics are never overwritten.
    $stmt = $conn->prepare(
        "UPDATE questions
         SET topic = ?,
             subject = COALESCE(NULLIF(?, ''), subject)
         WHERE question_id = ?
           AND (topic IS NULL OR topic = '')"
    );"""
new_guard = """    // Fill the topic when it is missing OR is a placeholder (e.g. "PG 2020", "Neet pg 2020")
    // so curated topics are never overwritten but junk ones get fixed.
    $stmt = $conn->prepare(
        "UPDATE questions
         SET topic = ?,
             subject = COALESCE(NULLIF(?, ''), subject)
         WHERE question_id = ?
           AND (topic IS NULL OR topic = ''
                OR topic REGEXP '[0-9]{4}|^PG|^Neet|^pg$')"
    );"""
assert old_guard in ut, "update_question_topic guard pattern not found"
ut = ut.replace(old_guard, new_guard)
open("tmp_php/update_question_topic.php", "w", encoding="utf-8").write(ut)
print("patched update_question_topic.php")

# --- 3) Deploy ---
ftp = CustomFTP()
ftp.connect(HOST, 21, timeout=30)
ftp.login(USER, PASS)
ftp.set_pasv(True)

def upload(remote, local, backup=False):
    if backup:
        try:
            ftp.rename(remote, remote + ".bak-20260904")
            print("backed up", remote)
        except Exception as e:
            print("backup failed (may exist):", remote, e)
    with open(local, "rb") as f:
        ftp.storbinary("STOR " + remote, f)
    print("uploaded", remote)

upload("/api/getQuestions.php", "tmp_php/getQuestions.php", backup=True)
upload("/api/update_question_topic.php", "tmp_php/update_question_topic.php")
upload("/api/generate_questions_ai.php", "tmp_php/generate_questions_ai.php")
ftp.quit()
