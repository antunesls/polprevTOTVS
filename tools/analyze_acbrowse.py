import pyodbc, struct

c = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;DATABASE=TOTVS_2510;"
    "UID=TOTVS12;PWD=TOTVS12"
)
r = c.cursor()
r.execute(
    "SELECT P_DEFS FROM MP_SYSTEM_PROFILE "
    "WHERE P_NAME='000002' AND P_PROG='SIGACOM' "
    "AND P_TYPE='ACBROWSE' AND D_E_L_E_T_=' '"
)
row = r.fetchone()

if row:
    data = bytes(row[0])
    pos = 0
    routine_overrides = {}
    routine = None

    while pos < len(data):
        if pos + 5 > len(data):
            break
        typ = chr(data[pos])
        val = struct.unpack_from("<I", data, pos + 1)[0]
        pos += 5
        if typ == "C":
            chunk = data[pos:pos + val]
            pos += val
            text = chunk.decode("ascii", errors="replace").strip("\0")
            if not routine:
                routine = text
            else:
                routine_overrides[routine] = text
                print(f"  {routine:12s} -> '{text}'")
                routine = None
        elif typ == "A":
            pass
        else:
            break

    print(f"\nTotal overrides: {len(routine_overrides)}")
    # Count disabled/partial
    full_access = sum(1 for v in routine_overrides.values() if v == "xxxxxxxxxx")
    partial = sum(1 for v in routine_overrides.values() if v != "xxxxxxxxxx" and any(c == ' ' for c in v))
    print(f"Full access: {full_access}, Partial: {partial}")

    # Show non-full ones
    print("\nNon-full access routines:")
    for k, v in routine_overrides.items():
        if v != "xxxxxxxxxx":
            print(f"  {k}: '{v}'")

c.close()
