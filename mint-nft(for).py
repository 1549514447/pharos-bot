#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FaroSwap Testnet Badge NFT Mint脚本 - 完全修正版
基于成功交易数据重新构建
"""

import asyncio
import json
import time
import os
from typing import Optional, List, Tuple
from pathlib import Path
import random

from web3 import Web3
from eth_account import Account
from colorama import *
from datetime import datetime
import pytz

# 初始化colorama
init()

# 时区设置
wib = pytz.timezone('Asia/Jakarta')


class FaroSwapBadgeMinter:
    """FaroSwap Testnet Badge NFT Mint机器人 - 完全修正版"""

    def __init__(self):
        # 网络配置 - 使用稳定的RPC
        self.RPC_URL = "https://api.zan.top/node/v1/pharos/testnet/0511efd49b7d435599fb3fb2bebb58b7"
        self.CHAIN_ID = 688688

        # 正确的NFT合约地址（用户确认）
        self.NFT_CONTRACT_ADDRESS = "0x2a469a4073480596b9deb19f52aa89891ccff5ce"

        # 合约ABI - claim函数
        self.CONTRACT_ABI = [
            {
                "inputs": [
                    {"internalType": "address", "name": "_receiver", "type": "address"},
                    {"internalType": "uint256", "name": "_quantity", "type": "uint256"},
                    {"internalType": "address", "name": "_currency", "type": "address"},
                    {"internalType": "uint256", "name": "_pricePerToken", "type": "uint256"},
                    {
                        "components": [
                            {"internalType": "bytes32[]", "name": "proof", "type": "bytes32[]"},
                            {"internalType": "uint256", "name": "quantityLimitPerWallet", "type": "uint256"},
                            {"internalType": "uint256", "name": "pricePerToken", "type": "uint256"},
                            {"internalType": "address", "name": "currency", "type": "address"}
                        ],
                        "internalType": "struct IDrop.AllowlistProof",
                        "name": "_allowlistProof",
                        "type": "tuple"
                    },
                    {"internalType": "bytes", "name": "_data", "type": "bytes"}
                ],
                "name": "claim",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "uint256", "name": "claimConditionIndex", "type": "uint256"},
                    {"indexed": True, "internalType": "address", "name": "claimer", "type": "address"},
                    {"indexed": True, "internalType": "address", "name": "receiver", "type": "address"},
                    {"indexed": False, "internalType": "uint256", "name": "startTokenId", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "quantityClaimed", "type": "uint256"}
                ],
                "name": "TokensClaimed",
                "type": "event"
            }
        ]

        # Mint参数 - 基于成功交易的完整数据
        self.MINT_PARAMS = {
            "quantity": 1,
            "currency": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
            "price_per_token": 1000000000000000000,  # 1 PHRS
            "allowlist_proof": {
                "proof": [],
                "quantityLimitPerWallet": 0,
                "pricePerToken": 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff,
                "currency": "0x0000000000000000000000000000000000000000"
            },
            "data": "0x"
        }

        self.w3 = None

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "\n" + "═" * 70)
        print(Fore.GREEN + Style.BRIGHT + "    🏆 FaroSwap Testnet Badge NFT Mint - 修正版 🏆")
        print(Fore.CYAN + Style.BRIGHT + "    ────────────────────────────────────────────────")
        print(Fore.YELLOW + Style.BRIGHT + "    🔧 基于成功交易数据完全重构")
        print(Fore.WHITE + Style.BRIGHT + "    💰 价格: 1 PHRS per NFT")
        print(Fore.WHITE + Style.BRIGHT + "    🌐 链ID: 688688 (Zentra Testnet)")
        print(Fore.WHITE + Style.BRIGHT + "    📝 方法: claim() - Public mint")
        print(Fore.WHITE + Style.BRIGHT + "    🎯 NFT: FaroSwap Testnet Badge")
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "═" * 70 + "\n")

    async def connect_to_network(self) -> bool:
        """连接到区块链网络"""
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.RPC_URL))

            # 测试连接
            block_number = await asyncio.to_thread(self.w3.eth.get_block_number)
            chain_id = self.w3.eth.chain_id

            if chain_id != self.CHAIN_ID:
                self.log(f"{Fore.RED + Style.BRIGHT}链ID不匹配: 期望 {self.CHAIN_ID}, 实际 {chain_id}{Style.RESET_ALL}")
                return False

            self.log(f"{Fore.GREEN + Style.BRIGHT}✅ 网络连接成功{Style.RESET_ALL}")
            self.log(f"{Fore.CYAN + Style.BRIGHT}   链ID: {chain_id}, 当前区块: {block_number}{Style.RESET_ALL}")
            return True

        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}❌ 网络连接失败: {str(e)}{Style.RESET_ALL}")
            return False

    async def check_balance(self, address: str) -> float:
        """检查账户PHRS余额"""
        try:
            balance_wei = await asyncio.to_thread(self.w3.eth.get_balance, address)
            balance_phrs = self.w3.from_wei(balance_wei, 'ether')
            return float(balance_phrs)
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}❌ 获取余额失败: {str(e)}{Style.RESET_ALL}")
            return 0.0

    async def verify_contract_address(self) -> bool:
        """验证合约地址是否正确"""
        try:
            # 检查合约代码是否存在
            code = await asyncio.to_thread(
                self.w3.eth.get_code,
                Web3.to_checksum_address(self.NFT_CONTRACT_ADDRESS)
            )

            if code == b'':
                self.log(f"{Fore.RED + Style.BRIGHT}❌ 合约地址无效: {self.NFT_CONTRACT_ADDRESS}{Style.RESET_ALL}")
                return False

            self.log(f"{Fore.GREEN + Style.BRIGHT}✅ 合约地址有效: {self.NFT_CONTRACT_ADDRESS}{Style.RESET_ALL}")
            return True

        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}❌ 验证合约地址失败: {str(e)}{Style.RESET_ALL}")
            return False

    async def estimate_gas_and_cost(self, address: str) -> Tuple[int, float]:
        """估算gas消耗和总成本"""
        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.NFT_CONTRACT_ADDRESS),
                abi=self.CONTRACT_ABI
            )

            # 构建交易数据
            mint_function = contract.functions.claim(
                Web3.to_checksum_address(address),
                self.MINT_PARAMS["quantity"],
                Web3.to_checksum_address(self.MINT_PARAMS["currency"]),
                self.MINT_PARAMS["price_per_token"],
                (
                    self.MINT_PARAMS["allowlist_proof"]["proof"],
                    self.MINT_PARAMS["allowlist_proof"]["quantityLimitPerWallet"],
                    self.MINT_PARAMS["allowlist_proof"]["pricePerToken"],
                    Web3.to_checksum_address(self.MINT_PARAMS["allowlist_proof"]["currency"])
                ),
                bytes.fromhex(self.MINT_PARAMS["data"][2:]) if self.MINT_PARAMS["data"] != "0x" else b""
            )

            # 估算gas
            estimated_gas = await asyncio.to_thread(
                mint_function.estimate_gas,
                {
                    "from": address,
                    "value": self.MINT_PARAMS["price_per_token"]
                }
            )

            # 计算总成本
            gas_price = self.w3.eth.gas_price
            gas_cost = estimated_gas * gas_price
            nft_cost = self.MINT_PARAMS["price_per_token"]
            total_cost_wei = nft_cost + gas_cost
            total_cost_phrs = self.w3.from_wei(total_cost_wei, 'ether')

            return estimated_gas, float(total_cost_phrs)

        except Exception as e:
            self.log(f"{Fore.YELLOW + Style.BRIGHT}⚠️ Gas估算失败: {str(e)}{Style.RESET_ALL}")
            return 200000, 1.01

    async def mint_nft(self, private_key: str, address: str) -> Tuple[bool, str]:
        """执行NFT mint - 完全按照成功交易重构"""
        try:
            # 检查余额
            balance = await self.check_balance(address)
            estimated_gas, total_cost = await self.estimate_gas_and_cost(address)

            self.log(f"{Fore.CYAN + Style.BRIGHT}💰 账户余额: {balance:.6f} PHRS{Style.RESET_ALL}")
            self.log(f"{Fore.CYAN + Style.BRIGHT}⛽ 预估Gas: {estimated_gas:,}{Style.RESET_ALL}")
            self.log(f"{Fore.CYAN + Style.BRIGHT}💸 预估总成本: {total_cost:.6f} PHRS{Style.RESET_ALL}")

            if balance < total_cost:
                error_msg = f"余额不足: 需要 {total_cost:.6f} PHRS, 当前 {balance:.6f} PHRS"
                self.log(f"{Fore.RED + Style.BRIGHT}❌ {error_msg}{Style.RESET_ALL}")
                return False, error_msg

            # 创建合约实例
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.NFT_CONTRACT_ADDRESS),
                abi=self.CONTRACT_ABI
            )

            # 构建mint交易 - 完全按照成功交易的参数
            mint_function = contract.functions.claim(
                Web3.to_checksum_address(address),  # receiver - 确保是用户地址
                self.MINT_PARAMS["quantity"],
                Web3.to_checksum_address(self.MINT_PARAMS["currency"]),
                self.MINT_PARAMS["price_per_token"],
                (
                    self.MINT_PARAMS["allowlist_proof"]["proof"],
                    self.MINT_PARAMS["allowlist_proof"]["quantityLimitPerWallet"],
                    self.MINT_PARAMS["allowlist_proof"]["pricePerToken"],
                    Web3.to_checksum_address(self.MINT_PARAMS["allowlist_proof"]["currency"])
                ),
                bytes.fromhex(self.MINT_PARAMS["data"][2:]) if self.MINT_PARAMS["data"] != "0x" else b""
            )

            # 获取nonce和gas价格 - 优化版本
            nonce = await asyncio.to_thread(self.w3.eth.get_transaction_count, address, "pending")

            # 智能Gas价格设置
            try:
                base_gas_price = self.w3.eth.gas_price
                # 提高gas价格以确保快速确认
                gas_price = int(base_gas_price * 1.5)  # 提高50%
                max_gas_price = self.w3.to_wei(5, "gwei")  # 最大5 Gwei
                gas_price = min(gas_price, max_gas_price)
            except:
                gas_price = self.w3.to_wei(2, "gwei")  # 备用gas价格

            self.log(
                f"{Fore.CYAN + Style.BRIGHT}⛽ 使用Gas价格: {self.w3.from_wei(gas_price, 'gwei'):.2f} Gwei{Style.RESET_ALL}")

            # 构建交易 - 添加超时保护
            transaction = mint_function.build_transaction({
                "from": address,
                "value": self.MINT_PARAMS["price_per_token"],
                "gas": int(estimated_gas * 1.3),  # 增加30%缓冲
                "gasPrice": gas_price,  # 使用优化的gas价格
                "nonce": nonce,
                "chainId": self.CHAIN_ID
            })

            # 打印调试信息
            self.log(f"{Fore.YELLOW + Style.BRIGHT}🔍 调试信息:{Style.RESET_ALL}")
            self.log(f"   合约地址: {self.NFT_CONTRACT_ADDRESS}")
            self.log(f"   接收者: {address}")
            self.log(f"   数量: {self.MINT_PARAMS['quantity']}")
            self.log(f"   价格: {self.MINT_PARAMS['price_per_token']} wei")
            self.log(f"   allowlist.pricePerToken: {hex(self.MINT_PARAMS['allowlist_proof']['pricePerToken'])}")

            # 签名交易
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)

            # 发送交易
            self.log(f"{Fore.YELLOW + Style.BRIGHT}📤 发送mint交易...{Style.RESET_ALL}")
            tx_hash = await asyncio.to_thread(
                self.w3.eth.send_raw_transaction, signed_txn.raw_transaction
            )
            tx_hash_hex = self.w3.to_hex(tx_hash)

            self.log(f"{Fore.CYAN + Style.BRIGHT}⏳ 等待交易确认: {tx_hash_hex}{Style.RESET_ALL}")

            # 等待交易确认 - 添加超时和重试机制
            try:
                # 先等待5秒看交易是否出现在pending中
                await asyncio.sleep(5)

                # 检查交易是否在pending池中
                try:
                    pending_tx = await asyncio.to_thread(self.w3.eth.get_transaction, tx_hash)
                    if pending_tx:
                        self.log(f"{Fore.GREEN + Style.BRIGHT}✅ 交易已进入pending池{Style.RESET_ALL}")
                except:
                    self.log(f"{Fore.YELLOW + Style.BRIGHT}⚠️ 交易可能还未广播到网络{Style.RESET_ALL}")

                # 等待确认，增加超时时间
                self.log(f"{Fore.CYAN + Style.BRIGHT}⏳ 等待区块确认 (最多10分钟)...{Style.RESET_ALL}")
                receipt = await asyncio.to_thread(
                    self.w3.eth.wait_for_transaction_receipt, tx_hash, timeout=600  # 10分钟超时
                )

            except Exception as timeout_error:
                self.log(f"{Fore.RED + Style.BRIGHT}❌ 交易确认超时: {str(timeout_error)}{Style.RESET_ALL}")
                self.log(f"{Fore.YELLOW + Style.BRIGHT}🔍 请手动检查交易: {tx_hash_hex}{Style.RESET_ALL}")
                self.log(
                    f"{Fore.YELLOW + Style.BRIGHT}🌐 浏览器: https://testnet.pharosscan.xyz/tx/{tx_hash_hex}{Style.RESET_ALL}")

                # 尝试再次检查交易状态
                try:
                    receipt = await asyncio.to_thread(self.w3.eth.get_transaction_receipt, tx_hash)
                    if receipt:
                        self.log(f"{Fore.GREEN + Style.BRIGHT}✅ 找到交易收据!{Style.RESET_ALL}")
                    else:
                        return False, f"交易超时且无法找到收据: {tx_hash_hex}"
                except:
                    return False, f"交易超时: {tx_hash_hex}"

            if receipt.status == 1:
                # 检查是否有Transfer事件
                transfer_found = False
                token_id = None

                for log in receipt.logs:
                    try:
                        # 检查Transfer事件 (ERC721)
                        if (log.topics[
                            0].hex() == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef" and
                                len(log.topics) >= 4):
                            # from = topics[1], to = topics[2], tokenId = topics[3]
                            from_addr = log.topics[1].hex()
                            to_addr = log.topics[2].hex()
                            token_id_raw = log.topics[3].hex()

                            # 检查是否是mint给用户的
                            if (from_addr == "0x" + "00" * 32 and  # from zero address
                                    to_addr.lower() == ("0x" + "00" * 12 + address[2:].lower())):  # to user
                                transfer_found = True
                                token_id = int(token_id_raw, 16)
                                break
                    except:
                        continue

                success_msg = f"Mint交易成功! TX: {tx_hash_hex}"
                if transfer_found and token_id:
                    success_msg += f", Token ID: #{token_id}"
                    self.log(f"{Fore.GREEN + Style.BRIGHT}✅ {success_msg}{Style.RESET_ALL}")
                    self.log(f"{Fore.GREEN + Style.BRIGHT}🎉 NFT已成功mint到您的地址!{Style.RESET_ALL}")
                else:
                    self.log(f"{Fore.YELLOW + Style.BRIGHT}⚠️ {success_msg}{Style.RESET_ALL}")
                    self.log(f"{Fore.YELLOW + Style.BRIGHT}⚠️ 未检测到NFT Transfer事件，请手动查看{Style.RESET_ALL}")

                return True, tx_hash_hex
            else:
                error_msg = f"交易失败: {tx_hash_hex}"
                self.log(f"{Fore.RED + Style.BRIGHT}❌ {error_msg}{Style.RESET_ALL}")
                return False, error_msg

        except Exception as e:
            error_msg = f"Mint异常: {str(e)}"
            self.log(f"{Fore.RED + Style.BRIGHT}❌ {error_msg}{Style.RESET_ALL}")
            return False, error_msg

    async def process_single_account(self, private_key: str) -> dict:
        """处理单个账户的mint"""
        try:
            account = Account.from_key(private_key)
            address = account.address

            self.log(f"{Fore.BLUE + Style.BRIGHT}🔄 处理账户: {address}{Style.RESET_ALL}")

            success, result = await self.mint_nft(private_key, address)

            return {
                "address": address,
                "success": success,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "address": "unknown",
                "success": False,
                "result": f"账户处理异常: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def process_accounts(self, private_keys: List[str], delay_range: Tuple[int, int] = (5, 15)):
        """批量处理账户mint"""
        results = []
        total_accounts = len(private_keys)

        self.log(f"{Fore.GREEN + Style.BRIGHT}🚀 开始批量mint: {total_accounts} 个账户{Style.RESET_ALL}")

        for i, private_key in enumerate(private_keys, 1):
            self.log(f"{Fore.CYAN + Style.BRIGHT}📋 进度: {i}/{total_accounts}{Style.RESET_ALL}")

            result = await self.process_single_account(private_key)
            results.append(result)

            if i < total_accounts:
                delay = random.randint(delay_range[0], delay_range[1])
                self.log(f"{Fore.YELLOW + Style.BRIGHT}⏳ 等待 {delay} 秒...{Style.RESET_ALL}")
                await asyncio.sleep(delay)

        return results

    def print_final_report(self, results: List[dict]):
        """打印最终报告"""
        print(f"\n{Fore.LIGHTGREEN_EX + Style.BRIGHT}{'=' * 80}")
        print(f"{Fore.GREEN + Style.BRIGHT}📊 FaroSwap Testnet Badge NFT Mint 报告")
        print(f"{Fore.LIGHTGREEN_EX + Style.BRIGHT}{'=' * 80}{Style.RESET_ALL}")

        total_accounts = len(results)
        successful_mints = sum(1 for r in results if r["success"])
        failed_mints = total_accounts - successful_mints
        success_rate = (successful_mints / total_accounts * 100) if total_accounts > 0 else 0

        print(f"{Fore.CYAN + Style.BRIGHT}📈 总体统计:{Style.RESET_ALL}")
        print(f"  总账户数: {total_accounts}")
        print(f"  成功Mint: {successful_mints}")
        print(f"  失败Mint: {failed_mints}")
        print(f"  成功率: {success_rate:.1f}%")

        print(f"\n{Fore.CYAN + Style.BRIGHT}📋 详细结果:{Style.RESET_ALL}")
        for i, result in enumerate(results, 1):
            status = "✅" if result["success"] else "❌"
            print(f"  {i:2d}. {result['address'][:10]}...{result['address'][-8:]} - {status}")
            if result["success"]:
                print(f"       交易: {result['result']}")
            else:
                print(f"       错误: {result['result']}")

        print(f"\n{Fore.GREEN + Style.BRIGHT}🏆 NFT合约信息:{Style.RESET_ALL}")
        print(f"  合约地址: {self.NFT_CONTRACT_ADDRESS}")
        print(f"  NFT名称: FaroSwap Testnet Badge")
        print(f"  Mint价格: {self.w3.from_wei(self.MINT_PARAMS['price_per_token'], 'ether')} PHRS")
        print(f"  网络: Zentra Testnet (ChainID: {self.CHAIN_ID})")

        if successful_mints > 0:
            print(
                f"\n{Fore.GREEN + Style.BRIGHT}🎉 恭喜! 成功mint了 {successful_mints} 个 FaroSwap Testnet Badge NFT!{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN + Style.BRIGHT}🔍 请在以下位置查看您的NFT:{Style.RESET_ALL}")
            print(f"  1. 区块链浏览器: https://testnet.pharosscan.xyz")
            print(f"  2. 搜索您的地址，查看NFT标签页")
            print(f"  3. 或在钱包中查看NFT收藏")

    async def main(self):
        """主函数"""
        try:
            self.clear_terminal()
            self.welcome()

            # 连接网络
            if not await self.connect_to_network():
                return

            # 验证合约地址
            if not await self.verify_contract_address():
                return

            # 加载私钥
            accounts_file = 'private_keys.txt'
            if not Path(accounts_file).exists():
                self.log(f"{Fore.RED}File '{accounts_file}' Not Found.{Style.RESET_ALL}")
                return

            with open(accounts_file, 'r') as file:
                private_keys = [line.strip() for line in file if line.strip()]

            if not private_keys:
                self.log(f"{Fore.RED}No private keys found in {accounts_file}{Style.RESET_ALL}")
                return

            self.log(f"{Fore.GREEN + Style.BRIGHT}📝 加载私钥: {len(private_keys)} 个{Style.RESET_ALL}")

            # 获取延迟设置
            print(f"\n{Fore.YELLOW + Style.BRIGHT}⏱️ 延迟设置:{Style.RESET_ALL}")
            min_delay = int(input(f"{Fore.BLUE + Style.BRIGHT}最小延迟 (秒, 默认5): {Style.RESET_ALL}").strip() or "5")
            max_delay = int(
                input(f"{Fore.BLUE + Style.BRIGHT}最大延迟 (秒, 默认15): {Style.RESET_ALL}").strip() or "15")

            print(f"\n{Fore.CYAN + Style.BRIGHT}🎯 Mint配置:{Style.RESET_ALL}")
            print(f"  NFT名称: FaroSwap Testnet Badge")
            print(f"  NFT数量: {self.MINT_PARAMS['quantity']} per address")
            print(f"  NFT价格: {self.w3.from_wei(self.MINT_PARAMS['price_per_token'], 'ether')} PHRS")
            print(f"  账户延迟: {min_delay}-{max_delay} 秒")
            print(f"  目标合约: {self.NFT_CONTRACT_ADDRESS}")
            print(f"  调试模式: 启用")

            # 重要警告
            print(f"\n{Fore.RED + Style.BRIGHT}⚠️ 重要提醒:{Style.RESET_ALL}")
            print(f"  如果此脚本仍然无法正确mint NFT，")
            print(f"  说明我们可能仍未找到正确的NFT合约地址。")
            print(f"  请提供您手动mint成功交易的完整 'To' 地址。")

            confirm = input(f"\n{Fore.BLUE + Style.BRIGHT}确认开始mint? (y/n): {Style.RESET_ALL}").lower()
            if confirm != 'y':
                self.log("已取消执行")
                return

            # 开始mint
            start_time = time.time()
            results = await self.process_accounts(private_keys, (min_delay, max_delay))
            end_time = time.time()

            # 生成报告
            self.print_final_report(results)

            self.log(f"{Fore.GREEN + Style.BRIGHT}⏱️ 总耗时: {end_time - start_time:.1f} 秒{Style.RESET_ALL}")

        except FileNotFoundError:
            self.log(f"{Fore.RED}File 'private_keys.txt' Not Found.{Style.RESET_ALL}")
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Error: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()


# 程序入口
if __name__ == "__main__":
    """
    FaroSwap Testnet Badge NFT Mint脚本 - 完全修正版

    基于成功交易数据重新构建，增加了详细的调试信息
    """

    try:
        print(f"{Fore.GREEN + Style.BRIGHT}")
        print("=" * 70)
        print("    🏆 FaroSwap Testnet Badge NFT Mint - 修正版")
        print("    🔧 基于成功交易数据完全重构")
        print("    💰 Price: 1 PHRS per NFT")
        print("    🌐 Network: Zentra Testnet (688688)")
        print("=" * 70)
        print(f"{Style.RESET_ALL}")

        minter = FaroSwapBadgeMinter()
        asyncio.run(minter.main())

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW + Style.BRIGHT}⚠️ 用户中断程序{Style.RESET_ALL}")
        print(f"{Fore.RED + Style.BRIGHT}[ EXIT ] FaroSwap NFT Minter - FIXED{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED + Style.BRIGHT}💥 程序异常退出: {e}{Style.RESET_ALL}")
        import traceback

        traceback.print_exc()
    finally:
        print(f"\n{Fore.GREEN + Style.BRIGHT}✨ 感谢使用 FaroSwap NFT Mint脚本!{Style.RESET_ALL}")