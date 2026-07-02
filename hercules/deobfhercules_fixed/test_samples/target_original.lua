-- target.lua
-- A small but non-trivial program: FNV-1a 32-bit hash + Base64 encoder
-- plus a tiny demo. Useful for testing deobfuscators: the algorithm is
-- well-known and easy to verify, but the obfuscator should hide it well.

local function fnv1a_32(text)
    local hash = 0x811c9dc5
    for i = 1, #text do
        local byte = string.byte(text, i)
        hash = hash ~ byte          -- XOR
        hash = (hash * 0x01000193) % 0x100000000
    end
    return hash
end

local BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

local function base64_encode(data)
    local out = {}
    local len = #data
    local i = 1
    while i <= len do
        local b1 = string.byte(data, i) or 0
        local b2 = string.byte(data, i + 1) or 0
        local b3 = string.byte(data, i + 2) or 0

        local n = b1 * 65536 + b2 * 256 + b3
        local c1 = math.floor(n / 262144) % 64
        local c2 = math.floor(n / 4096) % 64
        local c3 = math.floor(n / 64) % 64
        local c4 = n % 64

        out[#out + 1] = string.sub(BASE64_CHARS, c1 + 1, c1 + 1)
        out[#out + 1] = string.sub(BASE64_CHARS, c2 + 1, c2 + 1)
        if i + 1 <= len then
            out[#out + 1] = string.sub(BASE64_CHARS, c3 + 1, c3 + 1)
        else
            out[#out + 1] = "="
        end
        if i + 2 <= len then
            out[#out + 1] = string.sub(BASE64_CHARS, c4 + 1, c4 + 1)
        else
            out[#out + 1] = "="
        end
        i = i + 3
    end
    return table.concat(out)
end

local SECRET_KEY = "Hercules-Test-2026"

local function checksum(payload)
    return string.format("%08x", fnv1a_32(payload .. SECRET_KEY))
end

-- Demo
local samples = {
    "hello",
    "the quick brown fox",
    "Hercules was here",
}

print("=== Hercules Deobfuscation Challenge ===")
print("Target: recover fnv1a_32, base64_encode, checksum, SECRET_KEY")
print("")

for _, sample in ipairs(samples) do
    local b64 = base64_encode(sample)
    local sum = checksum(sample)
    print(string.format("input    : %q", sample))
    print(string.format("base64   : %s", b64))
    print(string.format("checksum : %s", sum))
    print("")
end

print("done.")
