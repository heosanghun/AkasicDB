import time
import os

# Set Hugging Face cache directory to E: drive due to C: drive space constraints
os.environ["HF_HOME"] = r"E:\AI\huggingface_cache"

import sqlite3
import json
import threading
from collections import defaultdict
from flask import Flask, request, jsonify, send_from_directory, Response
import sys
import random

try:
    import torch
    hf_device = "cuda" if torch.cuda.is_available() else "cpu"
except ImportError:
    hf_device = "cpu"

hf_model = None
hf_tokenizer = None

def load_hf_model():
    global hf_model, hf_tokenizer
    if hf_model is None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        try:
            model_name = "google/gemma-1.1-2b-it"
            print(f"Loading Hugging Face Model: {model_name} on {hf_device}...")
            hf_tokenizer = AutoTokenizer.from_pretrained(model_name)
            hf_model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16 if hf_device=="cuda" else torch.float32, low_cpu_mem_usage=True).to(hf_device)
        except Exception as e:
            print(f"Gemma load failed (might need HF token): {e}")
            model_name = "Qwen/Qwen1.5-1.8B-Chat"
            print(f"Falling back to {model_name}...")
            hf_tokenizer = AutoTokenizer.from_pretrained(model_name)
            hf_model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16 if hf_device=="cuda" else torch.float32, low_cpu_mem_usage=True).to(hf_device)
        print("Model loading complete!")

# Add parent directory to path to import akasic modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from akasic.storage.graph_store import GraphStore
from akasic.storage.relational_store import RelationalStore
from akasic.storage.vector_store import VectorStore
from akasic.query.planner import QueryPlanner

app = Flask(__name__, static_folder='../static', static_url_path='/static')

# Initialize SQLite DB (Feature 2: History DB)
def init_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, role TEXT, content TEXT, graph_data TEXT, results TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Initialize DB
g_store = GraphStore()
r_store = RelationalStore()
v_store = VectorStore()

def mock_embedding(text: str) -> list:
    # A simple deterministic hash to float vector for dummy embedding
    h = hash(text)
    return [float((h >> i) & 1) for i in range(10)]

def cosine_similarity(v1, v2):
    dot = sum(a*b for a,b in zip(v1, v2))
    mag1 = sum(a*a for a in v1)**0.5
    mag2 = sum(a*a for a in v2)**0.5
    if mag1*mag2 == 0: return 0
    return dot / (mag1*mag2)

def build_subgraph(start_nodes, g_store, depth=1):
    nodes = set(start_nodes)
    edges = []
    
    # Simple BFS for local subgraph
    queue = list(start_nodes)
    for _ in range(depth):
        next_q = []
        for src in queue:
            if src in g_store.edges:
                for edge_type, dst in g_store.edges[src]:
                    nodes.add(dst)
                    edges.append({"from": src, "to": dst, "label": edge_type})
                    next_q.append(dst)
        queue = next_q
    
    return {
        "nodes": [{"id": n, "label": n, "color": "#10a37f" if n in start_nodes else "#e2e8f0"} for n in nodes],
        "edges": edges
    }

def generate_large_synthetic_data():
    print("Generating 10,000+ synthetic entities... Please wait.")
    start_time = time.time()
    
    num_vessels = 50
    num_blocks = 200
    num_containers = 10000
    num_cranes = 20
    
    # 1. Generate normal random data
    blocks_per_vessel = num_blocks // num_vessels
    for v_id in range(num_vessels):
        v_name = f"Vessel_{v_id}"
        for b in range(blocks_per_vessel):
            b_name = f"YardBlock_{v_id * blocks_per_vessel + b}"
            g_store.add_edge(v_name, b_name, "discharges_to")
            
            chunk_text = f"Block {b_name} has {random.randint(10, 50)}% congestion."
            r_store.insert(b_name, {
                "type": "Block",
                "timestamp": f"2026-06-25 {random.randint(10, 23)}:00",
                "congestion": random.randint(10, 50),
                "chunk": chunk_text,
                "image_url": "/static/images/port_yard_block_1782369332880.png"
            })
            v_store.insert(b_name, mock_embedding(chunk_text))
            
    containers_per_block = num_containers // num_blocks
    for b_id in range(num_blocks):
        b_name = f"YardBlock_{b_id}"
        for c in range(containers_per_block):
            c_name = f"Container_{b_id * containers_per_block + c}"
            g_store.add_edge(b_name, c_name, "contains")
            
            crane_name = f"Crane_{random.randint(0, num_cranes - 1)}"
            g_store.add_edge(c_name, crane_name, "handled_by")
            
            chunk_text = f"Container {c_name} routine log. No special handling."
            r_store.insert(c_name, {
                "type": "Container",
                "timestamp": f"2026-06-25 {random.randint(10, 23)}:00",
                "chunk": chunk_text,
                "image_url": "/static/images/terminal_control_room_1782369354829.png"
            })
            v_store.insert(c_name, mock_embedding(chunk_text))
            
    for cr_id in range(num_cranes):
        cr_name = f"Crane_{cr_id}"
        chunk_text = f"Crane {cr_name} is operating normally."
        r_store.insert(cr_name, {
            "type": "Equipment",
            "timestamp": f"2026-06-25 {random.randint(10, 23)}:00",
            "chunk": chunk_text,
            "image_url": "/static/images/yard_crane_1782369342778.png"
        })
        v_store.insert(cr_name, mock_embedding(chunk_text))

    # 2. Inject Easter Eggs (User's specific scenarios)
    
    # Easter Egg 1: Block 3B Extra Moves
    b3b = "YardBlock_3B"
    c3b = "Container_3B_999"
    cr3b = "Crane_3B_X"
    g_store.add_edge("Vessel_Local", b3b, "discharges_to")
    g_store.add_edge(b3b, c3b, "contains")
    g_store.add_edge(c3b, cr3b, "handled_by")
    
    chunk_b3b = "3B 블록은 현재 컨테이너 추가 이송(Extra Moves) 횟수가 급증했습니다. 분석 결과, 화물 도착 정보 불일치로 인한 잦은 위치 재조정이 핵심 원인(Key Driver)으로 파악되었습니다."
    r_store.insert(b3b, {"type": "Block", "timestamp": "2026-06-25 15:00", "chunk": chunk_b3b, "image_url": "/static/images/port_yard_block_1782369332880.png"})
    v_store.insert(b3b, mock_embedding(chunk_b3b))
    
    chunk_c3b = "운영매뉴얼(SOP-3B): 추가 이송이 반복되는 컨테이너는 일시적으로 예비 공간에 적치하여 크레인 부하를 줄이십시오."
    r_store.insert(c3b, {"type": "Container", "timestamp": "2026-06-25 15:05", "chunk": chunk_c3b, "image_url": "/static/images/terminal_control_room_1782369354829.png"})
    v_store.insert(c3b, mock_embedding(chunk_c3b))
    
    chunk_cr3b = "크레인(Crane_3B_X) 로그: 무의미한 Shifting 작업이 연속 발생하여 전력 소모량이 한계치에 도달했습니다."
    r_store.insert(cr3b, {"type": "Equipment", "timestamp": "2026-06-25 15:10", "chunk": chunk_cr3b, "image_url": "/static/images/yard_crane_1782369342778.png"})
    v_store.insert(cr3b, mock_embedding(chunk_cr3b))

    # Easter Egg 2: Company A Cargo
    ca = "Container_Company_A"
    ba = "YardBlock_A_Buffer"
    g_store.add_edge("Vessel_Local", ba, "discharges_to")
    g_store.add_edge(ba, ca, "contains")
    chunk_ca = "특정 화주(A기업)의 화물 반출 패턴이 매우 불규칙하여 주변 컨테이너의 재취급률(Rehandling prob)을 극도로 높이고 있습니다."
    r_store.insert(ca, {"type": "Container", "timestamp": "2026-06-25 15:00", "chunk": chunk_ca, "image_url": "/static/images/terminal_control_room_1782369354829.png"})
    v_store.insert(ca, mock_embedding(chunk_ca))
    
    chunk_ba = "XAI 제안: A기업 전용 화물은 셔플링이 잦으므로, 게이트와 가장 가까운 'YardBlock_A_Buffer' 구역을 전용으로 할당하는 것이 최적입니다."
    r_store.insert(ba, {"type": "Block", "timestamp": "2026-06-25 15:05", "chunk": chunk_ba, "image_url": "/static/images/port_yard_block_1782369332880.png"})
    v_store.insert(ba, mock_embedding(chunk_ba))
    
    # Easter Egg 3: 1A Block Default
    g_store.add_edge("Vessel_Alpha", "YardBlock_1A", "discharges_to")
    g_store.add_edge("YardBlock_1A", "Container_YT102", "contains")
    g_store.add_edge("Container_YT102", "Crane_GC05", "handled_by")
    
    chunk_1a = "블록 1A는 고도 혼잡 상태를 보입니다(재취급 확률 +18.5% 증가). 원인은 'Vessel Alpha' 선박의 접안 지연 때문입니다."
    r_store.insert("YardBlock_1A", {"type": "Block", "timestamp": "2026-06-25 14:00", "chunk": chunk_1a, "image_url": "/static/images/port_yard_block_1782369332880.png"})
    v_store.insert("YardBlock_1A", mock_embedding(chunk_1a))
    
    chunk_1a_c = "운영매뉴얼(SOP-12): 블록 혼잡도가 높을 경우, 재취급을 방지하기 위해 야드 트랙터(YT102)를 임시 버퍼 존(Buffer zone)으로 우회시키십시오."
    r_store.insert("Container_YT102", {"type": "Container", "timestamp": "2026-06-25 14:10", "chunk": chunk_1a_c, "image_url": "/static/images/terminal_control_room_1782369354829.png"})
    v_store.insert("Container_YT102", mock_embedding(chunk_1a_c))
    
    # Easter Egg 4: Sims Reality
    sr_vessel = "Vessel_Sims"
    sr_block = "Block_Reality"
    sr_core = "Core_AI_Engine"
    g_store.add_edge(sr_vessel, sr_block, "partners_with")
    g_store.add_edge(sr_block, sr_core, "developed_by")
    
    chunk_sr_v = "심스리얼리티(Sims Reality)는 해양·항만 물류산업의 AX 혁신을 선도하는 최고 수준의 AI/XR 비전 기술 기업입니다."
    r_store.insert(sr_vessel, {"type": "Block", "timestamp": "2026-06-25 16:00", "chunk": chunk_sr_v, "image_url": "/static/images/sims_reality_logo.png"})
    v_store.insert(sr_vessel, mock_embedding(chunk_sr_v))
    
    chunk_sr_c = "현재 구동 중인 차세대 통합 데이터베이스 'AkasicDB'와 'Intelligent Yard Copilot' 대시보드의 원천 기술 파트너입니다."
    r_store.insert(sr_core, {"type": "Equipment", "timestamp": "2026-06-25 16:05", "chunk": chunk_sr_c, "image_url": "/static/images/sims_reality_logo.png"})
    v_store.insert(sr_core, mock_embedding(chunk_sr_c))

    print(f"Data generation complete in {time.time() - start_time:.2f} seconds. Total entities: {len(r_store.records)}")

generate_large_synthetic_data()
planner = QueryPlanner(g_store, r_store, v_store)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/query', methods=['POST'])
def query():
    data = request.json
    question = data.get("question", "")
    
    if "안녕" in question or question.strip() == "":
        return jsonify({
            "results": [],
            "graph_data": { 
                "nodes": [{"id": "Yard_Copilot", "label": "Yard Copilot", "color": "#10a37f"}], 
                "edges": [] 
            },
            "llm_response": "안녕하세요! 저는 항만 야드 운영 최적화를 돕는 'Intelligent Yard Copilot'입니다. 1만 개의 라이브 합성 데이터가 로드되었습니다! '3B 블록 추가 이송', 'A기업 화물 반출', '1A 블록 혼잡도' 등에 대해 질문해 보세요!"
        })

    # ... (Router logic same as provided in instructions)
    start_nodes = []
    if "3b" in question.lower() or "추가 이송" in question or "extra moves" in question.lower():
        start_nodes.extend(["Vessel_Local", "YardBlock_3B", "Container_3B_999"])
        llm_conclusion = "종합 안내: 화물 도착 정보 불일치 원인을 해결하기 위해 화주와의 시스템 연동을 재점검하고, 임시 예비 공간을 활용하십시오."
    elif "심스리얼리티" in question or "sims reality" in question.lower():
        start_nodes.extend(["Vessel_Sims", "Block_Reality", "Core_AI_Engine"])
        llm_conclusion = "종합 안내: 심스리얼리티(Sims Reality)는 차세대 RAG+XAI 항만 최적화 솔루션을 선도하는 핵심 개발 파트너입니다."
    elif "a기업" in question or "화주" in question or "반출 패턴" in question:
        start_nodes.extend(["Vessel_Local", "YardBlock_A_Buffer", "Container_Company_A"])
        llm_conclusion = "종합 안내: A기업의 화물은 게이트 인근의 'YardBlock_A_Buffer' 구역으로 집중 배치하여 터미널 재취급 비용을 절감하십시오."
    elif "1a" in question.lower() or "혼잡" in question:
        start_nodes.extend(["Vessel_Alpha", "YardBlock_1A", "Container_YT102"])
        llm_conclusion = "종합 안내: 불필요한 재취급(Rehandling)을 최소화하기 위해 해당 장비를 임시 버퍼 존으로 우회시킬 것을 강력히 권장합니다."
    else:
        start_nodes.extend([f"Vessel_0", f"YardBlock_0"])
        llm_conclusion = "종합 안내: 특별한 이상 징후가 발견되지 않았습니다. 정상적인 매뉴얼에 따라 운영하십시오."
        
    q_vec = mock_embedding(question)
    
    t0 = time.time()
    op_tree = planner.plan_omni_rag_query(
        start_entities=start_nodes,
        edge_type=None,
        filter_attr="type",
        filter_val=["Block", "Container", "Equipment"],
        filter_op="IN",
        query_vector=q_vec,
        limit=5
    )
    
    op_tree.open()
    results = []
    while True:
        r = op_tree.next()
        if not r: break
        results.append(r)
    op_tree.close()
    t1 = time.time()
    
    final_results = []
    chunk_summary = ""
    for r in results:
        dst = r["dst_id"]
        props = r_store.get(dst)
        chunk = props.get("chunk", "")
        chunk_summary += f"{dst} - {chunk} "
        final_results.append({
            "id": dst,
            "type": props.get("type", "Unknown"),
            "date": props.get("timestamp", ""),
            "chunk": chunk,
            "image_url": props.get("image_url", ""),
            "similarity": r["similarity"]
        })

    graph_data = build_subgraph(start_nodes, g_store, depth=1)
    
    return jsonify({
        "results": final_results,
        "graph_data": graph_data,
        "llm_response": f"[10,000+ 엔진 스캔 완료 (속도: {round(t1 - t0, 4)}ms)] RAG+XAI 분석 결과: {chunk_summary} {llm_conclusion}"
    })

# --- Session API Endpoints (Feature 2) ---

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT id, created_at FROM sessions ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "created_at": r[1]} for r in rows])

@app.route('/api/sessions', methods=['POST'])
def create_session():
    user = request.json.get("user", "Admin") if request.json else "Admin"
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("INSERT INTO sessions (user) VALUES (?)", (user,))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"id": session_id})

@app.route('/api/sessions/<int:session_id>/messages', methods=['GET'])
def get_messages(session_id):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT id, role, content, graph_data, results FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = c.fetchall()
    conn.close()
    messages = []
    for r in rows:
        messages.append({
            "id": r[0],
            "role": r[1],
            "content": r[2],
            "graph_data": json.loads(r[3]) if r[3] else None,
            "results": json.loads(r[4]) if r[4] else None
        })
    return jsonify(messages)

@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
def delete_session(session_id):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/stream_query', methods=['POST'])
def stream_query():
    data = request.json
    question = data.get("question", "")
    session_id = data.get("session_id")
    model_choice = data.get("model", "mock")
    
    start_nodes = []
    if "3b" in question.lower() or "추가 이송" in question or "extra moves" in question.lower():
        start_nodes.extend(["Vessel_Local", "YardBlock_3B", "Container_3B_999"])
        llm_conclusion = "종합 안내: 화물 도착 정보 불일치 원인을 해결하기 위해 화주와의 시스템 연동을 재점검하고, 임시 예비 공간을 활용하십시오."
    elif "심스리얼리티" in question or "sims reality" in question.lower():
        start_nodes.extend(["Vessel_Sims", "Block_Reality", "Core_AI_Engine"])
        llm_conclusion = "종합 안내: 심스리얼리티(Sims Reality)는 차세대 RAG+XAI 항만 최적화 솔루션을 선도하는 핵심 개발 파트너입니다. 현재 구동 중인 차세대 통합 데이터베이스 'AkasicDB'의 원천 기술을 보유하고 있습니다."
    elif "a기업" in question or "화주" in question or "반출 패턴" in question:
        start_nodes.extend(["Vessel_Local", "YardBlock_A_Buffer", "Container_Company_A"])
        llm_conclusion = "종합 안내: A기업의 화물은 게이트 인근의 'YardBlock_A_Buffer' 구역으로 집중 배치하여 터미널 재취급 비용을 절감하십시오."
    elif "1a" in question.lower() or "혼잡" in question:
        start_nodes.extend(["Vessel_Alpha", "YardBlock_1A", "Container_YT102"])
        llm_conclusion = "종합 안내: 불필요한 재취급(Rehandling)을 최소화하기 위해 해당 장비를 임시 버퍼 존으로 우회시킬 것을 강력히 권장합니다."
    else:
        start_nodes.extend([f"Vessel_0", f"YardBlock_0"])
        llm_conclusion = "종합 안내: 특별한 이상 징후가 발견되지 않았습니다. 정상적인 매뉴얼에 따라 운영하십시오."
        
    q_vec = mock_embedding(question)
    
    t0 = time.time()
    op_tree = planner.plan_omni_rag_query(
        start_entities=start_nodes,
        edge_type=None,
        filter_attr="type",
        filter_val=["Block", "Container", "Equipment"],
        filter_op="IN",
        query_vector=q_vec,
        limit=5
    )
    
    op_tree.open()
    results = []
    while True:
        r = op_tree.next()
        if not r: break
        results.append(r)
    op_tree.close()
    t1 = time.time()
    
    final_results = []
    chunk_summary = ""
    for r in results:
        dst = r["dst_id"]
        props = r_store.get(dst)
        chunk = props.get("chunk", "")
        chunk_summary += f"{dst} - {chunk} "
        final_results.append({
            "id": dst,
            "type": props.get("type", "Unknown"),
            "date": props.get("timestamp", ""),
            "chunk": chunk,
            "image_url": props.get("image_url", ""),
            "similarity": r["similarity"]
        })

    graph_data = build_subgraph(start_nodes, g_store, depth=1)
    
    if model_choice == "gemma":
        from transformers import TextIteratorStreamer
        
        def generate_hf():
            scan_time = f"{round(t1 - t0, 4)}"
            prefix = f"[10,000+ 엔진 스캔 완료 (속도: {scan_time}ms)] RAG+XAI 분석 결과 (Hugging Face 추론): "
            
            meta_payload = {
                "type": "metadata",
                "graph_data": graph_data,
                "results": final_results,
                "scan_time": scan_time
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"
            
            # 최초 다운로드 알림
            global hf_model
            if hf_model is None:
                yield f"data: {json.dumps({'type': 'token', 'text': '[시스템 알림: 첫 실행] 백그라운드에서 수 GB의 Hugging Face 모델(Gemma/Qwen)을 다운로드 중입니다. 파이썬 콘솔(터미널)을 열어 다운로드 프로그레스 바를 확인해 주세요. 인터넷 속도에 따라 수 분이 소요됩니다...\\n\\n'})}\n\n"
                
            # Load model lazily (blocks here on first run)
            load_hf_model()
            
            # Build prompt
            messages = [
                {"role": "system", "content": "You are an intelligent Port Yard Copilot. Answer the question based on the context provided. IMPORTANT: You must always answer in Korean (한국어)."},
                {"role": "user", "content": f"Context: {multimodal_prefix}\n{chunk_summary}\n\nQuestion: {question}"}
            ]
            prompt = hf_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = hf_tokenizer(prompt, return_tensors="pt").to(hf_device)
            streamer = TextIteratorStreamer(hf_tokenizer, skip_prompt=True, skip_special_tokens=True)
            
            generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=256)
            thread = threading.Thread(target=hf_model.generate, kwargs=generation_kwargs)
            thread.start()
            
            for char in prefix:
                yield f"data: {json.dumps({'type': 'token', 'text': char})}\n\n"
                time.sleep(0.01)
                
            llm_text = ""
            for new_text in streamer:
                llm_text += new_text
                yield f"data: {json.dumps({'type': 'token', 'text': new_text})}\n\n"
                
            if session_id:
                llm_full_text = prefix + llm_text
                conn = sqlite3.connect('chat_history.db')
                c = conn.cursor()
                c.execute("INSERT INTO messages (session_id, role, content, graph_data, results) VALUES (?, ?, ?, ?, ?)", 
                          (session_id, "user", question, None, None))
                c.execute("INSERT INTO messages (session_id, role, content, graph_data, results) VALUES (?, ?, ?, ?, ?)", 
                          (session_id, "ai", llm_full_text, json.dumps(graph_data), json.dumps(final_results)))
                conn.commit()
                conn.close()
                
            yield "data: [DONE]\n\n"
            
        return Response(generate_hf(), mimetype='text/event-stream')

    else:
        # SQLite DB 저장 로직 (Feature 2)
        if session_id:
            llm_full_text = f"[10,000+ 엔진 스캔 완료 (속도: {round(t1 - t0, 4)}ms)] RAG+XAI 분석 결과: {chunk_summary} {llm_conclusion}"
            conn = sqlite3.connect('chat_history.db')
            c = conn.cursor()
            c.execute("INSERT INTO messages (session_id, role, content, graph_data, results) VALUES (?, ?, ?, ?, ?)", 
                      (session_id, "user", question, None, None))
            c.execute("INSERT INTO messages (session_id, role, content, graph_data, results) VALUES (?, ?, ?, ?, ?)", 
                      (session_id, "ai", llm_full_text, json.dumps(graph_data), json.dumps(final_results)))
            conn.commit()
            conn.close()

        def generate_mock():
            scan_time = f"{round(t1 - t0, 4)}"
            prefix = f"[10,000+ 엔진 스캔 완료 (속도: {scan_time}ms)] RAG+XAI 분석 결과: "
            
            # 1. Send Metadata (Graph & Relational)
            meta_payload = {
                "type": "metadata",
                "graph_data": graph_data,
                "results": final_results,
                "scan_time": scan_time
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"
            
            # 2. Stream Prefix
            for char in prefix:
                yield f"data: {json.dumps({'type': 'token', 'text': char})}\n\n"
                time.sleep(0.01)
                
            # 3. Stream Chunk Evidence
            words = chunk_summary.split(' ')
            for word in words:
                if word:
                    yield f"data: {json.dumps({'type': 'token', 'text': word + ' '})}\n\n"
                    time.sleep(0.02)
                    
            # 4. Stream LLM Conclusion
            words = llm_conclusion.split(' ')
            for word in words:
                if word:
                    yield f"data: {json.dumps({'type': 'token', 'text': word + ' '})}\n\n"
                    time.sleep(0.05)
                    
            yield "data: [DONE]\n\n"

        return Response(generate_mock(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
