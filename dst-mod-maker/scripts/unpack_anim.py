#!/usr/bin/env python3
"""解包 DST 官方动画包（Klei Anim v4 / BILD v6）为可读 JSON。纯标准库、只读。

用途：拆开动画资源确认 bank、build、symbol、number、frame、layer 的真实命名及层级，不凭 zip 文件名猜。

输入：data/anim/<name>.zip（含 anim.bin / build.bin / atlas-*.tex）或单个 bin。
  anim.bin → bank 名、animation 名、每帧 element 的 symbol/layer hash + number + 变换
  build.bin → build 名、symbol → frames(number, duration) 表、atlas 页名

概念对照（务必分清，别混）：
  bank      = 动画集合名，来自 anim.bin 每个 animation 的 root hash（SetBank 用的名）
  build     = 贴图/符号集合名，来自 build.bin 的 build.name（SetBuild 用的名）
  symbol    = build 里的符号名（字符串）；OverrideSymbol 匹配的就是它
  number    = build frame 起始编号，或 anim element 引用编号（整数，非 hash）
  duration  = build frame 的 length，即覆盖的编号数量；左闭右开 [number, number+duration)
  frame     = build 下为贴图记录，animation 下为时间轴帧；element.number 不是动画帧号
              同 symbol 下按 build frame 的编号区间包含 element.number 查找贴图
  layer     = Spriter 图层名（element.layerName，字符串，可能与 symbol 不同名）
  atlas tex = 打包贴图页；symbol+number 区间匹配贴图记录，不输出顶点 UV

注意：symbol/layer/bank 在 bin 里存的是 Klei strhash，靠各文件尾部 hash 表还原；
个别旧包 name 未入表会显示 null，属正常，不要臆造名字。

格式依据：dst-lan 的 writeAnimBin/writeBuildBinFull 写入器（即格式定义），
已用本机 version.txt=762172 的官方动画包逐字节核对。
"""
import argparse
import json
import struct
import sys
import zipfile
from pathlib import Path


def _u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def _i32(b, o):
    return struct.unpack_from("<i", b, o)[0]


def _lstr(b, o):
    n = _i32(b, o)
    o += 4
    if n < 0 or o + n > len(b):
        raise ValueError(f"bad lenstring len {n} at {o - 4}")
    return b[o:o + n].decode("utf-8", "replace"), o + n


def _read_hash_table(b, o):
    """尾部: u32 count + 每条 (u32 hash, lenstring name) -> {str(hash): name}。"""
    out = {}
    if o + 4 > len(b):
        return out
    n = _u32(b, o)
    o += 4
    if n > (len(b) - o) // 8:  # sanity: 每条至少 8 字节
        return out
    for _ in range(n):
        h = _u32(b, o)
        o += 4
        s, o = _lstr(b, o)
        out[str(h)] = s
    return out


def parse_anim_bin(data):
    if len(data) < 24 or data[:4] != b"ANIM":
        raise ValueError("anim.bin: magic != ANIM")
    version = _i32(data, 4)
    if version != 4:
        raise ValueError(f"anim.bin: only v4 supported, got {version}")
    total_elements, total_frames, total_events, nanims = struct.unpack_from("<IIII", data, 8)
    o = 24
    anims = []
    for _ in range(nanims):
        name, o = _lstr(data, o)
        facing = data[o]
        o += 1
        bank_hash = _u32(data, o)
        o += 4
        fps = struct.unpack_from("<f", data, o)[0]
        o += 4
        nframes = _u32(data, o)
        o += 4
        frames = []
        for _ in range(nframes):
            x, y, w, h = struct.unpack_from("<ffff", data, o)
            o += 16
            nevents = _u32(data, o)
            o += 4
            events = []
            for _ in range(nevents):
                events.append(_u32(data, o))
                o += 4
            neles = _u32(data, o)
            o += 4
            elements = []
            for _ in range(neles):
                sym = _u32(data, o); o += 4
                number = _u32(data, o); o += 4
                layer = _u32(data, o); o += 4
                a, b, c, d, tx, ty, z = struct.unpack_from("<fffffff", data, o)
                o += 28
                elements.append({
                    "symbol_hash": sym, "number": number, "layer_hash": layer,
                    "a": a, "b": b, "c": c, "d": d, "tx": tx, "ty": ty, "zIndex": z,
                })
            frames.append({"x": x, "y": y, "w": w, "h": h,
                           "events": events, "elements": elements})
        anims.append({"name": name, "facing": facing, "bank_hash": bank_hash,
                      "fps": fps, "frames": frames})
    hashes = _read_hash_table(data, o)
    for a in anims:
        a["bank"] = hashes.get(str(a["bank_hash"]))
        for fr in a["frames"]:
            fr["event_names"] = [hashes.get(str(e)) for e in fr["events"]]
            for el in fr["elements"]:
                el["symbol"] = hashes.get(str(el["symbol_hash"]))
                el["layer"] = hashes.get(str(el["layer_hash"]))
    return {
        "version": version,
        "declared": {"elements": total_elements, "frames": total_frames,
                     "events": total_events, "anims": nanims},
        "animations": anims,
        "hash_names": hashes,
    }


def parse_build_bin(data):
    if len(data) < 16 or data[:4] != b"BILD":
        raise ValueError("build.bin: magic != BILD")
    version = _i32(data, 4)
    if version != 6:
        raise ValueError(f"build.bin: only v6 supported, got {version}")
    nsym, ntot = struct.unpack_from("<II", data, 8)
    o = 16
    name, o = _lstr(data, o)          # build 名（真正 SetBuild 用的）
    npage = _u32(data, o); o += 4
    pages = []
    for _ in range(npage):
        p, o = _lstr(data, o)
        pages.append(p)
    symbols = []
    for _ in range(nsym):
        sym_hash = _u32(data, o); o += 4
        nframes = _u32(data, o); o += 4
        frames = []
        for _ in range(nframes):
            number = _u32(data, o)
            duration = _u32(data, o + 4)
            x, y, w, h = struct.unpack_from("<ffff", data, o + 8)
            o += 24  # number, duration, 4 float
            o += 8   # fi.idx, fi.count
            frames.append({"number": number, "duration": duration,
                           "x": x, "y": y, "w": w, "h": h})
        symbols.append({"symbol_hash": sym_hash, "frames": frames})
    # symbol 表之后是 allVerts 顶点缓冲: u32 count + 每顶点 6 float(24 字节)
    nverts = _u32(data, o)
    o += 4 + nverts * 24
    hashes = _read_hash_table(data, o)
    for s in symbols:
        s["name"] = hashes.get(str(s["symbol_hash"]))
    return {
        "version": version, "build": name, "atlas_pages": pages,
        "declared": {"symbols": nsym, "frames": ntot},
        "symbols": symbols,
    }


def load_parts(src):
    """返回 (anim_bytes or None, build_bytes or None)。"""
    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as z:
            names = z.namelist()
            anim = next((z.read(n) for n in names if n.lower().endswith("anim.bin")), None)
            build = next((z.read(n) for n in names if n.lower().endswith("build.bin")), None)
            return anim, build
    raw = src.read_bytes()
    if raw[:4] == b"ANIM":
        return raw, None
    if raw[:4] == b"BILD":
        return None, raw
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="DST 动画 zip 或 anim.bin / build.bin")
    ap.add_argument("-o", "--out", help="输出 JSON 路径（默认 stdout）")
    ap.add_argument("--summary", action="store_true", help="只打印摘要")
    args = ap.parse_args()
    src = Path(args.input)
    if not src.is_file():
        print(f"ERROR: no such file: {src}", file=sys.stderr)
        return 2
    try:
        anim_b, build_b = load_parts(src)
    except zipfile.BadZipFile as e:
        print(f"ERROR: bad zip {src.name}: {e}", file=sys.stderr)
        return 1
    result = {"source": src.name}
    if anim_b:
        result["anim"] = parse_anim_bin(anim_b)
    if build_b:
        result["build"] = parse_build_bin(build_b)
    if not anim_b and not build_b:
        print(f"ERROR: {src.name} 内没有 anim.bin 或 build.bin（纯资源包？）", file=sys.stderr)
        return 1

    if args.summary:
        a = result.get("anim")
        b = result.get("build")
        if b:
            print(f"build   : {b['build']}  (symbols={b['declared']['symbols']}, pages={b['atlas_pages']})")
        if a:
            banks = sorted({x["bank"] for x in a["animations"] if x.get("bank")})
            print(f"bank    : {', '.join(str(x) for x in banks)}")
            print(f"anims   : {len(a['animations'])}  frames={a['declared']['frames']}")
            for x in a["animations"]:
                print(f"  {x['name']:<34} bank={x.get('bank')} frames={len(x['frames'])} fps={x['fps']}")
        if b:
            print(f"symbols : {', '.join(str(s.get('name')) for s in b['symbols'][:12])}")
    else:
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
