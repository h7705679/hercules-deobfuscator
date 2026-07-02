-- Lua 5.3+ / Luau compatibility polyfills
if not math.ldexp then math.ldexp = function(x, n) return x * 2 ^ n end end
if not math.frexp then math.frexp = function(x)
    if x == 0 then return 0, 0 end
    local exp = math.floor(math.log(math.abs(x)) / math.log(2)) + 1
    local mantissa = x / 2 ^ exp
    return mantissa, exp
end end
if not loadstring and load then loadstring = load end
if not loadstring then loadstring = function(s) return load(s) end end

--[Obfuscated by Hercules v2.0.0 | hercules-obfuscator.xyz/discord | hercules-obfuscator.xyz/source]
local thing = 4458;
local thing2 = 4458;
local counter = 0;
while thing == thing2 and counter < 1 do
    thing = thing + 1;
    counter = counter + 1;
    if thing == thing2 then
        local x = 25; x = x - 7;
    else
        do
            local oZwxpLYzH,TZFzqhxKSlZ,kLCbfyula,QTlTXgCAWApz,hRWMVYNmdzn,FPtliLoljlQL,uzJWScrcQ,YDRRkavOM,yoeCuEBIekXh,lomZOCfMAe
oZwxpLYzH=ipairs;TZFzqhxKSlZ=pairs;kLCbfyula=print;QTlTXgCAWApz=math.floor;hRWMVYNmdzn=string.byte;FPtliLoljlQL=string.char;uzJWScrcQ=string.format;YDRRkavOM=string.sub;yoeCuEBIekXh=table.concat;lomZOCfMAe=table.insert;
local function fGZkmybsQB(GiaRWPKm)
    return (GiaRWPKm >= 48 and GiaRWPKm <= 57) or (GiaRWPKm >= 65 and GiaRWPKm <= 90) or (GiaRWPKm >= 97 and GiaRWPKm <= 122)
end

local function aagffBSZSMO(DPanoQNVjUR, hyLGyzVIwWV)
    local nWEXuZGIdpNw = {}
    for bTNdNVMH = 1, #DPanoQNVjUR do
        local GiaRWPKm = DPanoQNVjUR:byte(bTNdNVMH)
        if fGZkmybsQB(GiaRWPKm) then
            local EBCuWhaqYXqz            if GiaRWPKm >= 48 and GiaRWPKm <= 57 then
                EBCuWhaqYXqz = ((GiaRWPKm - 48 - hyLGyzVIwWV + 10) % 10) + 48
            elseif GiaRWPKm >= 65 and GiaRWPKm <= 90 then
                EBCuWhaqYXqz = ((GiaRWPKm - 65 - hyLGyzVIwWV + 26) % 26) + 65
            elseif GiaRWPKm >= 97 and GiaRWPKm <= 122 then
                EBCuWhaqYXqz = ((GiaRWPKm - 97 - hyLGyzVIwWV + 26) % 26) + 97
            end
            table.insert(nWEXuZGIdpNw, string.char(EBCuWhaqYXqz))
        else
            table.insert(nWEXuZGIdpNw, string.char(GiaRWPKm))
        end
    end
    return table.concat(nWEXuZGIdpNw)
end

-- target.lua
-- A small but non-trivial program: FNV-1a 32-bit hash + Base64 encoder
-- plus a tiny demo. Useful for testing deobfuscators: the algorithm is
-- well-known and easy to verify, but the obfuscator should hide it well.

local function LjVgXlloc(text)
    local YoXshSiEZs = 0x811c9dc5
    for bTNdNVMH = 1, #text do
        local fNSivElvGh = string.byte(text, bTNdNVMH)
        YoXshSiEZs = YoXshSiEZs ~ fNSivElvGh          -- XOR
        YoXshSiEZs = (YoXshSiEZs * 0x01000193) % 0x100000000
    end
    return YoXshSiEZs
end

local PKKiBmYZzJSq = aagffBSZSMO("ZABCDEFGHIJKLMNOPQRSTUVWXYzabcdefghijklmnopqrstuvwxy5678901234+/", 25)

local function ZAIeOxcniWqm(data)
    local GDuFQNEfATGU = {}
    local FGTGeBTCNq = #data
    local bTNdNVMH = 1
    while bTNdNVMH <= FGTGeBTCNq do
        local MSnUPFhsvbVM = string.byte(data, bTNdNVMH) or 0
        local uNWlJZZSU = string.byte(data, bTNdNVMH + 1) or 0
        local CaqVFXWhj = string.byte(data, bTNdNVMH + 2) or 0

        local gMueaozuU = MSnUPFhsvbVM * 65536 + uNWlJZZSU * 256 + CaqVFXWhj
        local EPmMTebnAhZH = math.floor(gMueaozuU / 262144) % 64
        local dKeZZZku = math.floor(gMueaozuU / 4096) % 64
        local CgtkpxUnV = math.floor(gMueaozuU / 64) % 64
        local rCbXeAzu = gMueaozuU % 64

        GDuFQNEfATGU[#GDuFQNEfATGU + 1] = string.sub(PKKiBmYZzJSq, EPmMTebnAhZH + 1, EPmMTebnAhZH + 1)
        GDuFQNEfATGU[#GDuFQNEfATGU + 1] = string.sub(PKKiBmYZzJSq, dKeZZZku + 1, dKeZZZku + 1)
        if bTNdNVMH + 1 <= FGTGeBTCNq then
            GDuFQNEfATGU[#GDuFQNEfATGU + 1] = string.sub(PKKiBmYZzJSq, CgtkpxUnV + 1, CgtkpxUnV + 1)
        else
            GDuFQNEfATGU[#GDuFQNEfATGU + 1] = aagffBSZSMO("=", 1)
        end
        if bTNdNVMH + 2 <= FGTGeBTCNq then
            GDuFQNEfATGU[#GDuFQNEfATGU + 1] = string.sub(PKKiBmYZzJSq, rCbXeAzu + 1, rCbXeAzu + 1)
        else
            GDuFQNEfATGU[#GDuFQNEfATGU + 1] = aagffBSZSMO("=", 1)
        end
        bTNdNVMH = bTNdNVMH + 3
    end
    return table.concat(GDuFQNEfATGU)
end

local ruGEgfebPj = aagffBSZSMO("Danyqhao-Paop-4248", 22)

local function hglFwWLTu(payload)
    return string.format(aagffBSZSMO("%19y", 1), LjVgXlloc(payload .. ruGEgfebPj))
end

-- Demo
local rYVNvjioWJ = {
    aagffBSZSMO("ebiil", 23),
    aagffBSZSMO("rfc osgai zpmul dmv", 24),
    aagffBSZSMO("Gdqbtkdr vzr gdqd", 25),
}

kLCbfyula(aagffBSZSMO("=== Gdqbtkdr Cdnaetrbzshnm Bgzkkdmfd ===", 25))
kLCbfyula(aagffBSZSMO("Szqfds: qdbnudq emu6z_87, azrd19_dmbncd, bgdbjrtl, RDBQDS_JDX", 25))
kLCbfyula(aagffBSZSMO("", 1))

for _, sample in oZwxpLYzH(rYVNvjioWJ) do
    local CMjnKczw = ZAIeOxcniWqm(sample)
    local TbTYDoYl = hglFwWLTu(sample)
    kLCbfyula(string.format(aagffBSZSMO("glnsr    : %o", 24), sample))
    kLCbfyula(string.format(aagffBSZSMO("azrd19   : %r", 25), CMjnKczw))
    kLCbfyula(string.format(aagffBSZSMO("afcaiqsk : %q", 24), TbTYDoYl))
    kLCbfyula(aagffBSZSMO("", 1))
end

kLCbfyula(aagffBSZSMO("cnmd.", 25))

        end
        break
    end
end
local dummy = 1; dummy = dummy + 6;
