This tool checks your non-redeemable tokens to identify which ones are eligible for claiming 14-day Nitro trial gifts using old (invalid or valid) linked payment methods.
Tokens marked as Eligible can successfully claim Nitro gifts and act just like receiver tokens — no vcc required.

❌ Tokens shown as Ineligible in this script are not usable for claiming gifts with this method.

🔧 Fast, multi-threaded, proxy-supported checker
📄 Input: tokens.txt + proxies.txt
📝 Output: output.txt (Eligible / Ineligible)


no skidding pls 🙏

| Condition                                                     | Result       |
| ------------------------------------------------------------- | ------------ |
| No payment history                                            | Ineligible ❌ |
| Last payment < 30 days ago                                    | Ineligible ❌ |
| Has active Nitro subscription                                 | Ineligible ❌ |
| Has **invalid card** + last payment >= 30 days ago + no Nitro | ✅ Eligible   |
| Has **only valid card(s)** or no card at all                  | Ineligible ❌ |
