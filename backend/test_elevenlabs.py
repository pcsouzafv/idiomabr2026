"""
Script de teste para o módulo de conversação ElevenLabs
Testa as principais funcionalidades da API
"""
import sys
import os

# Adiciona o diretório pai ao path para importar módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.elevenlabs_service import elevenlabs_service
from app.core.config import get_settings


def test_api_key():
    """Testa se a API key está configurada"""
    print("=" * 60)
    print("🔑 Testando configuração da API Key...")
    print("=" * 60)
    
    settings = get_settings()
    
    if not settings.elevenlabs_api_key:
        print("❌ ERRO: ELEVENLABS_API_KEY não configurada!")
        print("   Configure no arquivo .env")
        return False
    
    print(f"✅ API Key configurada: {settings.elevenlabs_api_key[:10]}...")
    print(f"✅ Voice ID padrão: {settings.elevenlabs_voice_id}")
    return True


def test_list_voices():
    """Testa listagem de vozes"""
    print("\n" + "=" * 60)
    print("🎤 Testando listagem de vozes...")
    print("=" * 60)
    
    try:
        voices = elevenlabs_service.get_voices()
        print(f"✅ {len(voices)} vozes disponíveis:")
        
        for i, voice in enumerate(voices[:5], 1):
            print(f"   {i}. {voice.get('name', 'Unknown')} (ID: {voice.get('voice_id', 'N/A')})")
        
        if len(voices) > 5:
            print(f"   ... e mais {len(voices) - 5} vozes")
        
        return True
    except Exception as e:
        print(f"❌ ERRO ao listar vozes: {str(e)}")
        return False


def test_text_to_speech():
    """Testa conversão de texto em fala"""
    print("\n" + "=" * 60)
    print("🔊 Testando Text-to-Speech...")
    print("=" * 60)
    
    test_text = "Hello! This is a test of the ElevenLabs text to speech system."
    print(f"Texto: '{test_text}'")
    
    try:
        audio_data = elevenlabs_service.text_to_speech(test_text)
        
        if not audio_data:
            print("❌ ERRO: Nenhum dado de áudio retornado")
            return False
        
        print(f"✅ Áudio gerado com sucesso! ({len(audio_data)} bytes)")
        
        # Salva arquivo de teste
        output_file = "test_audio.mp3"
        with open(output_file, "wb") as f:
            f.write(audio_data)
        
        print(f"✅ Áudio salvo em: {output_file}")
        print("   Você pode reproduzir o arquivo para verificar a qualidade")
        
        return True
    except ValueError as e:
        print(f"❌ ERRO de configuração: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ ERRO ao gerar áudio: {str(e)}")
        return False


def test_conversation_session():
    """Testa criação de sessão de conversação"""
    print("\n" + "=" * 60)
    print("💬 Testando criação de sessão de conversação...")
    print("=" * 60)
    
    try:
        session = elevenlabs_service.create_conversation_session(
            system_prompt="You are a helpful English teacher."
        )
        
        print(f"✅ Sessão criada com sucesso (TTS-only mode)!")
        print(f"   ID: {session.get('conversation_id', 'N/A')[:30]}...")
        print(f"   Status: {session.get('status', 'N/A')}")
        print(f"   Voice ID: {session.get('voice_id', 'N/A')}")
        print(f"   Nota: {session.get('note', '')}")
        
        return True
    except NotImplementedError:
        print("⚠️  Endpoint de conversação não implementado na API ElevenLabs")
        print("   (isso é normal - usando modo TTS-only com IA backend)")
        return True
    except Exception as e:
        print(f"❌ ERRO ao criar sessão: {str(e)}")
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "=" * 60)
    print("🧪 TESTE DO MÓDULO DE CONVERSAÇÃO ELEVENLABS")
    print("=" * 60)
    
    results = {
        "API Key": test_api_key(),
        "Listar Vozes": test_list_voices(),
        "Text-to-Speech": test_text_to_speech(),
        "Sessão de Conversação": test_conversation_session()
    }
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\n{total_passed}/{total_tests} testes passaram")
    
    if total_passed == total_tests:
        print("\n🎉 Todos os testes passaram! O módulo está funcionando corretamente.")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os erros acima.")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
