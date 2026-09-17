def test_ffmpeg_detected(client):
    from reviewforge.config import load_config
    from reviewforge.util.ffmpeg import check_ffmpeg_available

    config = load_config()
    availability = check_ffmpeg_available(config)
    assert availability.ffmpeg_found, "ffmpeg must be installed and on PATH for this test"
    assert availability.ffprobe_found, "ffprobe must be installed and on PATH for this test"
    assert availability.version is not None
