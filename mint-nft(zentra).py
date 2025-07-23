#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zentra Testnet Badge NFT Mint脚本
基于您提供的交易数据分析编写
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
import requests
from datetime import datetime
import pytz

# 初始化colorama
init()

# 时区设置
wib = pytz.timezone('Asia/Jakarta')


class ZentraTestnetBadgeMinter:
    """Zentra Testnet Badge NFT Mint机器人"""

    def __init__(self):
        # 网络配置
        self.RPC_URL = "https://testnet.dplabs-internal.com"  # 根据ChainID 688688推测
        self.CHAIN_ID = 688688

        # 合约地址 (从交易数据获取)
        self.NFT_CONTRACT_ADDRESS = "0xe71188df7be6321ffd5aaa6e52e6c96375e62793"

        # 合约ABI - mint相关的函数
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

        # Mint参数 (从交易数据分析得出)
        self.MINT_PARAMS = {
            "quantity": 1,  # 每次mint数量
            "currency": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # ETH/PHRS原生代币
            "price_per_token": 1000000000000000000,  # 1 PHRS (1 * 10^18 wei)
            "allowlist_proof": {
                "proof": [],  # 空数组，表示公开mint
                "quantityLimitPerWallet": 0,  # 无限制
                "pricePerToken": 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff,  # 最大值
                "currency": "0x0000000000000000000000000000000000000000"  # 零地址
            },
            "data": "0x"  # 空bytes
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
        print(Fore.GREEN + Style.BRIGHT + "    🎨 Zentra Testnet Badge NFT Mint脚本 🎨")
        print(Fore.CYAN + Style.BRIGHT + "    ──────────────────────────────────────")
        print(Fore.YELLOW + Style.BRIGHT + "    🏷️  合约: 0xe71188...75e62793")
        print(Fore.WHITE + Style.BRIGHT + "    💰 价格: 1 PHRS per NFT")
        print(Fore.WHITE + Style.BRIGHT + "    🌐 链ID: 688688 (Zentra Testnet)")
        print(Fore.WHITE + Style.BRIGHT + "    📝 方法: claim() - Public mint")
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "═" * 70 + "\n")

    async def connect_to_network(self) -> bool:
        """连接到区块链网络"""
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.RPC_URL))

            # 测试连接
            block_number = await asyncio.to_thread(self.w3.eth.get_block_number)
            chain_id = self.w3.eth.chain_id  # 直接访问属性，不需要异步

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

    async def estimate_gas_and_cost(self, address: str) -> Tuple[int, float]:
        """估算gas消耗和总成本"""
        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.NFT_CONTRACT_ADDRESS),
                abi=self.CONTRACT_ABI
            )

            # 构建交易数据
            mint_function = contract.functions.claim(
                Web3.to_checksum_address(address),  # receiver
                self.MINT_PARAMS["quantity"],  # quantity
                Web3.to_checksum_address(self.MINT_PARAMS["currency"]),  # currency
                self.MINT_PARAMS["price_per_token"],  # pricePerToken
                (
                    self.MINT_PARAMS["allowlist_proof"]["proof"],
                    self.MINT_PARAMS["allowlist_proof"]["quantityLimitPerWallet"],
                    self.MINT_PARAMS["allowlist_proof"]["pricePerToken"],
                    Web3.to_checksum_address(self.MINT_PARAMS["allowlist_proof"]["currency"])
                ),  # allowlistProof
                bytes.fromhex(self.MINT_PARAMS["data"][2:]) if self.MINT_PARAMS["data"] != "0x" else b""  # data
            )

            # 估算gas
            estimated_gas = await asyncio.to_thread(
                mint_function.estimate_gas,
                {
                    "from": address,
                    "value": self.MINT_PARAMS["price_per_token"]  # NFT价格
                }
            )

            # 计算总成本 (NFT价格 + Gas费用)
            gas_price = self.w3.eth.gas_price  # 直接访问属性
            gas_cost = estimated_gas * gas_price
            nft_cost = self.MINT_PARAMS["price_per_token"]
            total_cost_wei = nft_cost + gas_cost
            total_cost_phrs = self.w3.from_wei(total_cost_wei, 'ether')

            return estimated_gas, float(total_cost_phrs)

        except Exception as e:
            self.log(f"{Fore.YELLOW + Style.BRIGHT}⚠️ Gas估算失败: {str(e)}{Style.RESET_ALL}")
            # 返回保守估算值
            return 200000, 1.01  # 大约1.01 PHRS

    async def mint_nft(self, private_key: str, address: str) -> Tuple[bool, str]:
        """执行NFT mint"""
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

            # 构建mint交易
            mint_function = contract.functions.claim(
                Web3.to_checksum_address(address),  # receiver
                self.MINT_PARAMS["quantity"],  # quantity
                Web3.to_checksum_address(self.MINT_PARAMS["currency"]),  # currency
                self.MINT_PARAMS["price_per_token"],  # pricePerToken
                (
                    self.MINT_PARAMS["allowlist_proof"]["proof"],
                    self.MINT_PARAMS["allowlist_proof"]["quantityLimitPerWallet"],
                    self.MINT_PARAMS["allowlist_proof"]["pricePerToken"],
                    Web3.to_checksum_address(self.MINT_PARAMS["allowlist_proof"]["currency"])
                ),  # allowlistProof
                bytes.fromhex(self.MINT_PARAMS["data"][2:]) if self.MINT_PARAMS["data"] != "0x" else b""  # data
            )

            # 获取nonce和gas价格
            nonce = await asyncio.to_thread(self.w3.eth.get_transaction_count, address, "pending")
            gas_price = self.w3.eth.gas_price  # 直接访问属性

            # 构建交易
            transaction = mint_function.build_transaction({
                "from": address,
                "value": self.MINT_PARAMS["price_per_token"],  # NFT价格
                "gas": int(estimated_gas * 1.2),  # 增加20%的gas buffer
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": self.CHAIN_ID
            })

            # 签名交易
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)

            # 发送交易
            self.log(f"{Fore.YELLOW + Style.BRIGHT}📤 发送mint交易...{Style.RESET_ALL}")
            tx_hash = await asyncio.to_thread(
                self.w3.eth.send_raw_transaction, signed_txn.raw_transaction
            )
            tx_hash_hex = self.w3.to_hex(tx_hash)

            self.log(f"{Fore.CYAN + Style.BRIGHT}⏳ 等待交易确认: {tx_hash_hex}{Style.RESET_ALL}")

            # 等待交易确认
            receipt = await asyncio.to_thread(
                self.w3.eth.wait_for_transaction_receipt, tx_hash, timeout=300
            )

            if receipt.status == 1:
                # 解析事件日志获取tokenId
                token_id = None
                try:
                    contract_instance = self.w3.eth.contract(
                        address=Web3.to_checksum_address(self.NFT_CONTRACT_ADDRESS),
                        abi=self.CONTRACT_ABI
                    )

                    # 解析TokensClaimed事件
                    for log in receipt.logs:
                        try:
                            decoded_log = contract_instance.events.TokensClaimed().process_log(log)
                            token_id = decoded_log['args']['startTokenId']
                            break
                        except:
                            continue
                except:
                    pass

                success_msg = f"Mint成功! TX: {tx_hash_hex}"
                if token_id:
                    success_msg += f", Token ID: #{token_id}"

                self.log(f"{Fore.GREEN + Style.BRIGHT}✅ {success_msg}{Style.RESET_ALL}")
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
            # 生成地址
            account = Account.from_key(private_key)
            address = account.address

            self.log(f"{Fore.BLUE + Style.BRIGHT}🔄 处理账户: {address}{Style.RESET_ALL}")

            # 执行mint
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

            # 处理账户
            result = await self.process_single_account(private_key)
            results.append(result)

            # 延迟 (除了最后一个账户)
            if i < total_accounts:
                delay = random.randint(delay_range[0], delay_range[1])
                self.log(f"{Fore.YELLOW + Style.BRIGHT}⏳ 等待 {delay} 秒...{Style.RESET_ALL}")
                await asyncio.sleep(delay)

        return results

    def print_final_report(self, results: List[dict]):
        """打印最终报告"""
        print(f"\n{Fore.LIGHTGREEN_EX + Style.BRIGHT}{'=' * 80}")
        print(f"{Fore.GREEN + Style.BRIGHT}📊 Zentra Testnet Badge NFT Mint 报告")
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

        print(f"\n{Fore.GREEN + Style.BRIGHT}🎨 NFT合约信息:{Style.RESET_ALL}")
        print(f"  合约地址: {self.NFT_CONTRACT_ADDRESS}")
        print(f"  NFT名称: Zentra Testnet Badge")
        print(f"  Mint价格: {self.w3.from_wei(self.MINT_PARAMS['price_per_token'], 'ether')} PHRS")
        print(f"  网络: Zentra Testnet (ChainID: {self.CHAIN_ID})")

        if successful_mints > 0:
            print(
                f"\n{Fore.GREEN + Style.BRIGHT}🎉 恭喜! 成功mint了 {successful_mints} 个 Zentra Testnet Badge NFT!{Style.RESET_ALL}")

    async def main(self):
        """主函数"""
        try:
            self.clear_terminal()
            self.welcome()

            # 连接网络
            if not await self.connect_to_network():
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
            print(f"\n{Fore.YELLOW + Style.BRIGHT}⏱️ 延迟设置 (防止RPC过载):{Style.RESET_ALL}")
            min_delay = int(input(f"{Fore.BLUE + Style.BRIGHT}最小延迟 (秒, 默认5): {Style.RESET_ALL}").strip() or "5")
            max_delay = int(
                input(f"{Fore.BLUE + Style.BRIGHT}最大延迟 (秒, 默认15): {Style.RESET_ALL}").strip() or "15")

            print(f"\n{Fore.CYAN + Style.BRIGHT}🎯 Mint配置:{Style.RESET_ALL}")
            print(f"  NFT数量: {self.MINT_PARAMS['quantity']} per address")
            print(f"  NFT价格: {self.w3.from_wei(self.MINT_PARAMS['price_per_token'], 'ether')} PHRS")
            print(f"  账户延迟: {min_delay}-{max_delay} 秒")
            print(f"  目标合约: {self.NFT_CONTRACT_ADDRESS}")

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
    Zentra Testnet Badge NFT Mint脚本

    功能:
    1. 🎨 自动mint Zentra Testnet Badge NFT
    2. 💰 自动计算mint成本和gas费用
    3. 📊 批量处理多个账户
    4. ⏱️ 智能延迟防止RPC过载
    5. 📋 详细的mint报告

    使用方法:
    1. 将私钥放入 private_keys.txt 文件 (每行一个)
    2. 确保账户有足够的PHRS (至少1.01 PHRS per mint)
    3. 运行脚本开始mint
    """

    try:
        print(f"{Fore.GREEN + Style.BRIGHT}")
        print("=" * 70)
        print("    🎨 Zentra Testnet Badge NFT Mint脚本启动中...")
        print("    💰 Price: 1 PHRS per NFT")
        print("    🌐 Network: Zentra Testnet (688688)")
        print("=" * 70)
        print(f"{Style.RESET_ALL}")

        minter = ZentraTestnetBadgeMinter()
        asyncio.run(minter.main())

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW + Style.BRIGHT}⚠️ 用户中断程序{Style.RESET_ALL}")
        print(f"{Fore.RED + Style.BRIGHT}[ EXIT ] Zentra NFT Minter - BOT{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED + Style.BRIGHT}💥 程序异常退出: {e}{Style.RESET_ALL}")
        import traceback

        traceback.print_exc()
    finally:
        print(f"\n{Fore.GREEN + Style.BRIGHT}✨ 感谢使用 Zentra Testnet Badge NFT Mint脚本!{Style.RESET_ALL}")