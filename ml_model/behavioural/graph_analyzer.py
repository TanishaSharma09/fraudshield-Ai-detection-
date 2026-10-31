"""FraudShield AI - Account Relationship & Network Graph Analyzer.

Analyzes transactional relationship topologies between accounts:
- Constructs directed multi-account interaction graphs (Nodes: Accounts, Edges: Directed Transfers).
- Computes pair interaction metrics: frequency, total volume, risk concentration, repeated cycles.
- Identifies AML topologies:
    * Mule Hubs (fan-in from multiple victims or fan-out dispersal).
    * Ping-Pong / Circular Fund Routing (A -> B -> A).
    * Repeated Burst Interactions (high velocity between specific synthetic account pairs).
- Generates JSON network payloads for frontend Canvas/SVG relationship visualisers.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import numpy as np

from database.connection import query_all


@dataclass
class NetworkNode:
    """Represents an account node in the financial relationship graph."""
    id: str
    label: str
    role: str  # "SENDER", "RECEIVER", "MULE_HUB", "BALANCED"
    total_sent: float = 0.0
    total_received: float = 0.0
    tx_sent_count: int = 0
    tx_recv_count: int = 0
    avg_risk_score: float = 0.0
    max_risk_score: float = 0.0
    is_mule_candidate: bool = False
    is_suspicious: bool = False
    is_simulated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "role": self.role,
            "total_sent": round(self.total_sent, 2),
            "total_received": round(self.total_received, 2),
            "tx_sent_count": self.tx_sent_count,
            "tx_recv_count": self.tx_recv_count,
            "avg_risk_score": round(self.avg_risk_score, 1),
            "max_risk_score": round(self.max_risk_score, 1),
            "is_mule_candidate": self.is_mule_candidate,
            "is_suspicious": self.is_suspicious,
            "is_simulated": self.is_simulated,
        }


@dataclass
class NetworkEdge:
    """Represents a directed payment relationship between two accounts."""
    id: str
    source: str
    target: str
    tx_count: int
    total_amount: float
    avg_risk_score: float
    max_risk_score: float
    is_suspicious: bool
    is_repeated: bool
    channels: list[str]
    last_timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "tx_count": self.tx_count,
            "total_amount": round(self.total_amount, 2),
            "avg_risk_score": round(self.avg_risk_score, 1),
            "max_risk_score": round(self.max_risk_score, 1),
            "is_suspicious": self.is_suspicious,
            "is_repeated": self.is_repeated,
            "channels": self.channels,
            "last_timestamp": self.last_timestamp,
        }


class AccountRelationshipGraphAnalyzer:
    """Service computing account relationship graphs and detecting mule networks."""

    @staticmethod
    def _is_simulated_vpa(vpa: str) -> bool:
        """Determines if an account is synthetic or demonstration based."""
        v = vpa.lower()
        sim_keywords = [
            "demo", "mule", "unknown", "crypto", "fast.cash",
            "test", "synthetic", "bot", "hacker", "attack"
        ]
        return any(k in v for k in sim_keywords)

    def build_graph_from_records(
        self,
        transactions: list[dict[str, Any]],
        min_risk_score: float = 0.0,
        only_suspicious: bool = False,
    ) -> dict[str, Any]:
        """Builds directed relationship graph and detects network clusters from transaction records."""
        edge_map: dict[tuple[str, str], dict[str, Any]] = {}
        node_stats: dict[str, dict[str, Any]] = {}

        for tx in transactions:
            sender = str(tx.get("sender_upi", "")).strip().lower()
            receiver = str(tx.get("receiver_upi", "")).strip().lower()
            if not sender or not receiver:
                continue

            amt = float(tx.get("amount", 0.0))
            score = float(tx.get("risk_score", 0.0))
            channel = str(tx.get("channel", "UPI_APP"))
            ts = tx.get("timestamp") or datetime.now(timezone.utc).isoformat()
            is_flg = int(tx.get("is_flagged", 0)) == 1 or score >= 40.0

            # 1. Update Edge Aggregation
            key = (sender, receiver)
            if key not in edge_map:
                edge_map[key] = {
                    "source": sender,
                    "target": receiver,
                    "tx_count": 0,
                    "total_amount": 0.0,
                    "scores": [],
                    "channels": set(),
                    "latest_ts": ts,
                    "is_flagged": False,
                }
            e = edge_map[key]
            e["tx_count"] += 1
            e["total_amount"] += amt
            e["scores"].append(score)
            e["channels"].add(channel)
            if is_flg:
                e["is_flagged"] = True
            if ts > e["latest_ts"]:
                e["latest_ts"] = ts

            # 2. Update Sender Node Stats
            if sender not in node_stats:
                node_stats[sender] = {
                    "sent_amt": 0.0, "recv_amt": 0.0,
                    "sent_cnt": 0, "recv_cnt": 0,
                    "scores": [], "distinct_partners": set(),
                }
            node_stats[sender]["sent_amt"] += amt
            node_stats[sender]["sent_cnt"] += 1
            node_stats[sender]["scores"].append(score)
            node_stats[sender]["distinct_partners"].add(receiver)

            # 3. Update Receiver Node Stats
            if receiver not in node_stats:
                node_stats[receiver] = {
                    "sent_amt": 0.0, "recv_amt": 0.0,
                    "sent_cnt": 0, "recv_cnt": 0,
                    "scores": [], "distinct_partners": set(),
                }
            node_stats[receiver]["recv_amt"] += amt
            node_stats[receiver]["recv_cnt"] += 1
            node_stats[receiver]["scores"].append(score)
            node_stats[receiver]["distinct_partners"].add(sender)

        # 4. Construct Final Edges
        final_edges: list[NetworkEdge] = []
        circular_pairs: set[frozenset[str]] = set()

        for (s, r), data in edge_map.items():
            cnt = data["tx_count"]
            avg_score = float(np.mean(data["scores"]))
            max_score = float(max(data["scores"]))
            is_repeated = cnt >= 2
            is_susp = data["is_flagged"] or max_score >= 60.0 or (is_repeated and avg_score >= 35.0)

            # Check for circular ping-pong
            if (r, s) in edge_map:
                circular_pairs.add(frozenset([s, r]))

            if only_suspicious and not is_susp:
                continue
            if max_score < min_risk_score:
                continue

            edge_obj = NetworkEdge(
                id=f"edge-{s}->{r}",
                source=s,
                target=r,
                tx_count=cnt,
                total_amount=data["total_amount"],
                avg_risk_score=avg_score,
                max_risk_score=max_score,
                is_suspicious=is_susp,
                is_repeated=is_repeated,
                channels=sorted(list(data["channels"])),
                last_timestamp=data["latest_ts"],
            )
            final_edges.append(edge_obj)

        # 5. Construct Final Nodes
        active_node_ids = {e.source for e in final_edges}.union({e.target for e in final_edges})
        final_nodes: list[NetworkNode] = []
        mule_hubs_count = 0

        for nid, stats in node_stats.items():
            if nid not in active_node_ids and only_suspicious:
                continue

            avg_node_score = float(np.mean(stats["scores"])) if stats["scores"] else 0.0
            max_node_score = float(max(stats["scores"])) if stats["scores"] else 0.0

            # Mule Hub Heuristic: High receiver volume/in-degree with low out-degree, or sudden aggregation
            is_mule = (
                stats["recv_cnt"] >= 2 and
                (stats["recv_amt"] >= 20000.0 or len(stats["distinct_partners"]) >= 2) and
                (avg_node_score >= 40.0 or "mule" in nid or "crypto" in nid)
            )
            if is_mule:
                mule_hubs_count += 1
                role = "MULE_HUB"
            elif stats["sent_cnt"] > stats["recv_cnt"] * 2:
                role = "SENDER"
            elif stats["recv_cnt"] > stats["sent_cnt"] * 2:
                role = "RECEIVER"
            else:
                role = "BALANCED"

            is_node_susp = is_mule or avg_node_score >= 40.0 or max_node_score >= 70.0
            is_sim = self._is_simulated_vpa(nid)

            node_obj = NetworkNode(
                id=nid,
                label=nid.split("@")[0],
                role=role,
                total_sent=stats["sent_amt"],
                total_received=stats["recv_amt"],
                tx_sent_count=stats["sent_cnt"],
                tx_recv_count=stats["recv_cnt"],
                avg_risk_score=avg_node_score,
                max_risk_score=max_node_score,
                is_mule_candidate=is_mule,
                is_suspicious=is_node_susp,
                is_simulated=is_sim,
            )
            final_nodes.append(node_obj)

        # If graph is empty (e.g. freshly initialized test database), provide demonstration topology
        if not final_nodes:
            return self.get_demonstration_graph()

        return {
            "nodes": [n.to_dict() for n in final_nodes],
            "edges": [e.to_dict() for e in final_edges],
            "metrics": {
                "total_nodes": len(final_nodes),
                "total_edges": len(final_edges),
                "suspicious_edges_count": sum(1 for e in final_edges if e.is_suspicious),
                "repeated_interaction_pairs": sum(1 for e in final_edges if e.is_repeated),
                "mule_hubs_detected": mule_hubs_count,
                "circular_routing_detected": len(circular_pairs),
            },
        }

    def build_graph_from_db(
        self,
        min_risk_score: float = 0.0,
        only_suspicious: bool = False,
        limit: int = 500,
        db_path: str | None = None,
    ) -> dict[str, Any]:
        """Queries SQLite stored transactions to produce the live account relationship graph."""
        sql = f"""
            SELECT 
                tx_id,
                sender_upi,
                receiver_upi,
                amount,
                risk_score,
                risk_tier,
                status,
                is_flagged,
                channel,
                timestamp
            FROM transactions
            ORDER BY timestamp DESC
            LIMIT ?;
        """
        rows = query_all(sql, (limit,), db_path=db_path)
        records = [dict(r) for r in rows]
        return self.build_graph_from_records(
            transactions=records,
            min_risk_score=min_risk_score,
            only_suspicious=only_suspicious,
        )

    def get_demonstration_graph(self) -> dict[str, Any]:
        """Realistic baseline synthetic account relationship graph."""
        demo_nodes = [
            {"id": "vikram.patel@okhdfcbank", "label": "vikram.patel", "role": "SENDER", "total_sent": 85000.0, "total_received": 0.0, "tx_sent_count": 2, "tx_recv_count": 0, "avg_risk_score": 92.5, "max_risk_score": 95.0, "is_mule_candidate": False, "is_suspicious": True, "is_simulated": True},
            {"id": "unknown.mule.crypto@ybl", "label": "mule.crypto", "role": "MULE_HUB", "total_sent": 0.0, "total_received": 142000.0, "tx_sent_count": 0, "tx_recv_count": 5, "avg_risk_score": 88.0, "max_risk_score": 95.0, "is_mule_candidate": True, "is_suspicious": True, "is_simulated": True},
            {"id": "neha.gupta@paytm", "label": "neha.gupta", "role": "SENDER", "total_sent": 24000.0, "total_received": 0.0, "tx_sent_count": 3, "tx_recv_count": 0, "avg_risk_score": 76.0, "max_risk_score": 82.0, "is_mule_candidate": False, "is_suspicious": True, "is_simulated": True},
            {"id": "fast.cash.collect@axl", "label": "fast.cash.collect", "role": "MULE_HUB", "total_sent": 0.0, "total_received": 57000.0, "tx_sent_count": 0, "tx_recv_count": 4, "avg_risk_score": 78.4, "max_risk_score": 85.0, "is_mule_candidate": True, "is_suspicious": True, "is_simulated": True},
            {"id": "arjun.sharma@okaxis", "label": "arjun.sharma", "role": "SENDER", "total_sent": 3800.0, "total_received": 0.0, "tx_sent_count": 4, "tx_recv_count": 0, "avg_risk_score": 12.0, "max_risk_score": 18.0, "is_mule_candidate": False, "is_suspicious": False, "is_simulated": True},
            {"id": "nature.groceries@icici", "label": "nature.groceries", "role": "RECEIVER", "total_sent": 0.0, "total_received": 3800.0, "tx_sent_count": 0, "tx_recv_count": 4, "avg_risk_score": 12.0, "max_risk_score": 18.0, "is_mule_candidate": False, "is_suspicious": False, "is_simulated": True},
            {"id": "synthetic.mule.ring1@ybl", "label": "mule.ring1", "role": "MULE_HUB", "total_sent": 45000.0, "total_received": 85000.0, "tx_sent_count": 2, "tx_recv_count": 3, "avg_risk_score": 84.0, "max_risk_score": 90.0, "is_mule_candidate": True, "is_suspicious": True, "is_simulated": True},
        ]
        demo_edges = [
            {"id": "edge-vikram->mule", "source": "vikram.patel@okhdfcbank", "target": "unknown.mule.crypto@ybl", "tx_count": 2, "total_amount": 85000.0, "avg_risk_score": 94.8, "max_risk_score": 95.0, "is_suspicious": True, "is_repeated": True, "channels": ["INTENT_FLOW"], "last_timestamp": datetime.now(timezone.utc).isoformat()},
            {"id": "edge-neha->fastcash", "source": "neha.gupta@paytm", "target": "fast.cash.collect@axl", "tx_count": 3, "total_amount": 29400.0, "avg_risk_score": 78.4, "max_risk_score": 84.0, "is_suspicious": True, "is_repeated": True, "channels": ["COLLECT_REQUEST"], "last_timestamp": datetime.now(timezone.utc).isoformat()},
            {"id": "edge-arjun->grocery", "source": "arjun.sharma@okaxis", "target": "nature.groceries@icici", "tx_count": 4, "total_amount": 3800.0, "avg_risk_score": 11.5, "max_risk_score": 15.0, "is_suspicious": False, "is_repeated": True, "channels": ["QR_CODE"], "last_timestamp": datetime.now(timezone.utc).isoformat()},
            {"id": "edge-mule->ring1", "source": "unknown.mule.crypto@ybl", "target": "synthetic.mule.ring1@ybl", "tx_count": 2, "total_amount": 45000.0, "avg_risk_score": 86.0, "max_risk_score": 89.0, "is_suspicious": True, "is_repeated": True, "channels": ["INTENT_FLOW"], "last_timestamp": datetime.now(timezone.utc).isoformat()},
        ]
        return {
            "nodes": demo_nodes,
            "edges": demo_edges,
            "metrics": {
                "total_nodes": len(demo_nodes),
                "total_edges": len(demo_edges),
                "suspicious_edges_count": 3,
                "repeated_interaction_pairs": 4,
                "mule_hubs_detected": 3,
                "circular_routing_detected": 1,
            },
        }


# Singleton instance helper
_graph_analyzer: AccountRelationshipGraphAnalyzer | None = None


def get_graph_analyzer() -> AccountRelationshipGraphAnalyzer:
    """Returns or initialises the singleton AccountRelationshipGraphAnalyzer."""
    global _graph_analyzer
    if _graph_analyzer is None:
        _graph_analyzer = AccountRelationshipGraphAnalyzer()
    return _graph_analyzer
