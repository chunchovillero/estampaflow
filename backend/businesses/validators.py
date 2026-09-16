import re
from rest_framework import serializers

def normalize_chilean_phone(value,required=False):
    value=(value or "").strip()
    if not value and not required:return ""
    digits=re.sub(r"\D","",value)
    if digits.startswith("56"):digits=digits[2:]
    if len(digits)!=9 or digits[0] not in "23456789":raise serializers.ValidationError("Ingresa un teléfono chileno válido, por ejemplo +56912345678.")
    return f"+56{digits}"

def normalize_rut(value):
    value=(value or "").strip().upper().replace(".","").replace("-","")
    if not value:return ""
    if not re.fullmatch(r"\d{7,8}[0-9K]",value):raise serializers.ValidationError("Ingresa un RUT válido.")
    body,verifier=value[:-1],value[-1];total=0;factor=2
    for digit in reversed(body):
        total+=int(digit)*factor;factor=2 if factor==7 else factor+1
    expected=11-(total%11);expected="0" if expected==11 else "K" if expected==10 else str(expected)
    if verifier!=expected:raise serializers.ValidationError("El dígito verificador del RUT no es válido.")
    return f"{int(body):,}".replace(",",".")+f"-{verifier}"
