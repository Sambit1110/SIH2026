from app.core.forensics.relay_trace import reconstruct_relay_chain


def test_reorders_to_chronological_and_flags_private_ip():
    # header order: index 0 = most recent (closest to recipient), last = origin
    headers = [
        "from internal-mx.example.com (internal-mx.example.com [10.0.0.5]) by mx.example.com with LMTP id 3; Mon, 01 Sep 2026 10:05:00 +0000",
        "from mail.origin.net (mail.origin.net [93.184.216.34]) by mx.example.com with ESMTP id 2; Mon, 01 Sep 2026 10:04:00 +0000",
    ]
    hops = reconstruct_relay_chain(headers)
    assert len(hops) == 2
    # chronological order: origin hop first
    assert hops[0].ip == "93.184.216.34"
    assert hops[0].sequence == 1
    assert hops[1].ip == "10.0.0.5"
    assert "PRIVATE_IP" in hops[1].flags
    assert hops[0].is_earliest_reliable is True


def test_empty_received_headers():
    assert reconstruct_relay_chain([]) == []


def test_missing_ip_flagged():
    headers = ["from unknown-host by mx.example.com with ESMTP id 1; Mon, 01 Sep 2026 10:00:00 +0000"]
    hops = reconstruct_relay_chain(headers)
    assert hops[0].ip is None
    assert "NO_IP_OBSERVED" in hops[0].flags
