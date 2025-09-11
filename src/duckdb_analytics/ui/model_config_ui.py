"""
Model Configuration UI for Streamlit.

This module provides UI components for configuring LLM models
and generation parameters.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
import json
from pathlib import Path

from ..llm.model_config import (
    ModelConfigManager,
    ModelProfile,
    ModelProvider,
    GenerationMode,
    AdaptiveModelSelector
)


class ModelConfigUI:
    """UI component for model configuration."""
    
    def __init__(self, config_manager: Optional[ModelConfigManager] = None):
        """
        Initialize model configuration UI.
        
        Args:
            config_manager: Model configuration manager instance
        """
        self.config_manager = config_manager or ModelConfigManager()
        
        # Initialize session state
        if "model_profile" not in st.session_state:
            st.session_state.model_profile = self.config_manager.get_active_profile()
        if "generation_mode" not in st.session_state:
            st.session_state.generation_mode = GenerationMode.BALANCED
    
    def render_sidebar_config(self):
        """Render configuration in sidebar."""
        with st.sidebar:
            st.markdown("## 🤖 LLM Configuration")
            
            # Quick mode selector
            st.markdown("### Generation Mode")
            mode = st.select_slider(
                "Select mode",
                options=[
                    GenerationMode.FAST.value,
                    GenerationMode.BALANCED.value,
                    GenerationMode.THOROUGH.value
                ],
                value=st.session_state.generation_mode.value,
                format_func=lambda x: x.title(),
                help="Choose between speed and quality"
            )
            st.session_state.generation_mode = GenerationMode(mode)
            
            # Mode description
            mode_descriptions = {
                GenerationMode.FAST: "⚡ Quick responses, minimal analysis",
                GenerationMode.BALANCED: "⚖️ Balanced speed and quality",
                GenerationMode.THOROUGH: "🔍 Comprehensive analysis"
            }
            st.caption(mode_descriptions[st.session_state.generation_mode])
            
            # Profile selector
            st.markdown("### Model Profile")
            profiles = self.config_manager.list_profiles()
            selected_profile = st.selectbox(
                "Active profile",
                options=profiles,
                index=profiles.index(self.config_manager.active_profile) if self.config_manager.active_profile in profiles else 0,
                help="Select the model configuration profile"
            )
            
            if selected_profile != self.config_manager.active_profile:
                self.config_manager.set_active_profile(selected_profile)
                st.session_state.model_profile = self.config_manager.get_profile(selected_profile)
            
            # Quick optimization buttons
            st.markdown("### Quick Optimize")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⚡ Optimize Speed", use_container_width=True):
                    self.config_manager.optimize_for_latency(selected_profile)
                    st.success("Optimized for speed!")
                    st.rerun()
            
            with col2:
                if st.button("✨ Optimize Quality", use_container_width=True):
                    self.config_manager.optimize_for_quality(selected_profile)
                    st.success("Optimized for quality!")
                    st.rerun()
            
            # Advanced settings expander
            with st.expander("Advanced Settings", expanded=False):
                self._render_advanced_settings()
    
    def render_main_config_panel(self):
        """Render full configuration panel in main area."""
        st.markdown("## 🎛️ LLM Model Configuration")
        
        tabs = st.tabs(["Profile Settings", "Generation Parameters", "Performance", "Import/Export"])
        
        with tabs[0]:
            self._render_profile_settings()
        
        with tabs[1]:
            self._render_generation_parameters()
        
        with tabs[2]:
            self._render_performance_settings()
        
        with tabs[3]:
            self._render_import_export()
    
    def _render_advanced_settings(self):
        """Render advanced settings in sidebar."""
        profile = st.session_state.model_profile
        
        if not profile:
            st.warning("No profile selected")
            return
        
        # Temperature
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=profile.temperature,
            step=0.1,
            help="Controls randomness in generation"
        )
        
        # Max tokens
        max_tokens = st.slider(
            "Max Tokens",
            min_value=500,
            max_value=4000,
            value=profile.max_tokens,
            step=100,
            help="Maximum tokens to generate"
        )
        
        # Timeout
        timeout = st.slider(
            "Request Timeout (s)",
            min_value=1.0,
            max_value=30.0,
            value=profile.request_timeout,
            step=1.0,
            help="Maximum time to wait for response"
        )
        
        # Thinking depth
        thinking_depth = st.select_slider(
            "Thinking Depth",
            options=["minimal", "standard", "comprehensive"],
            value=profile.thinking_depth,
            help="How detailed should the thinking process be"
        )
        
        # Apply changes button
        if st.button("Apply Changes", type="primary", use_container_width=True):
            self.config_manager.update_profile(
                profile.name,
                temperature=temperature,
                max_tokens=max_tokens,
                request_timeout=timeout,
                thinking_depth=thinking_depth
            )
            st.success("Settings updated!")
            st.rerun()
    
    def _render_profile_settings(self):
        """Render profile settings tab."""
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Current Profile")
            profile = st.session_state.model_profile
            
            if profile:
                # Profile info
                st.write(f"**Name:** {profile.name}")
                st.write(f"**Provider:** {profile.provider.value}")
                st.write(f"**Model:** {profile.model_id}")
                
                # Edit profile name
                new_name = st.text_input("Profile Name", value=profile.name)
                
                # Model ID
                new_model_id = st.text_input("Model ID", value=profile.model_id)
                
                # Provider
                providers = [p.value for p in ModelProvider]
                provider_index = providers.index(profile.provider.value)
                new_provider = st.selectbox(
                    "Provider",
                    options=providers,
                    index=provider_index
                )
                
                # Save changes
                if st.button("Save Profile Changes"):
                    profile.name = new_name
                    profile.model_id = new_model_id
                    profile.provider = ModelProvider(new_provider)
                    self.config_manager.save_profile(profile.name)
                    st.success("Profile saved!")
            else:
                st.info("No profile selected")
        
        with col2:
            st.markdown("### Create New Profile")
            
            # New profile form
            with st.form("new_profile"):
                name = st.text_input("Profile Name")
                provider = st.selectbox("Provider", [p.value for p in ModelProvider])
                model_id = st.text_input("Model ID")
                base_mode = st.selectbox(
                    "Base Mode",
                    [m.value for m in GenerationMode],
                    format_func=lambda x: x.title()
                )
                
                if st.form_submit_button("Create Profile"):
                    if name and model_id:
                        new_profile = self.config_manager.create_profile(
                            name=name,
                            provider=ModelProvider(provider),
                            model_id=model_id,
                            mode=GenerationMode(base_mode)
                        )
                        self.config_manager.save_profile(name)
                        st.success(f"Profile '{name}' created!")
                        st.rerun()
                    else:
                        st.error("Please fill in all fields")
    
    def _render_generation_parameters(self):
        """Render generation parameters tab."""
        profile = st.session_state.model_profile
        
        if not profile:
            st.info("No profile selected")
            return
        
        st.markdown("### Generation Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Temperature
            temperature = st.slider(
                "🌡️ Temperature",
                min_value=0.0,
                max_value=1.0,
                value=profile.temperature,
                step=0.05,
                help="Lower = more focused, Higher = more creative"
            )
            
            # Top P
            top_p = st.slider(
                "📊 Top P",
                min_value=0.0,
                max_value=1.0,
                value=profile.top_p,
                step=0.05,
                help="Nucleus sampling parameter"
            )
            
            # Frequency penalty
            freq_penalty = st.slider(
                "🔁 Frequency Penalty",
                min_value=-2.0,
                max_value=2.0,
                value=profile.frequency_penalty,
                step=0.1,
                help="Reduce repetition"
            )
        
        with col2:
            # Max tokens
            max_tokens = st.number_input(
                "📝 Max Tokens",
                min_value=100,
                max_value=8000,
                value=profile.max_tokens,
                step=100,
                help="Maximum response length"
            )
            
            # Presence penalty
            pres_penalty = st.slider(
                "🆕 Presence Penalty",
                min_value=-2.0,
                max_value=2.0,
                value=profile.presence_penalty,
                step=0.1,
                help="Encourage new topics"
            )
            
            # Context tokens
            context_tokens = st.number_input(
                "📚 Max Context Tokens",
                min_value=1000,
                max_value=16000,
                value=profile.max_context_tokens,
                step=500,
                help="Maximum context window"
            )
        
        st.markdown("### Advanced Features")
        
        col3, col4 = st.columns(2)
        
        with col3:
            # Feature toggles
            use_chain = st.checkbox(
                "🔗 Chain of Thought",
                value=profile.use_chain_of_thought,
                help="Enable step-by-step reasoning"
            )
            
            use_reflection = st.checkbox(
                "🪞 Self-Reflection",
                value=profile.use_self_reflection,
                help="Enable self-evaluation"
            )
            
            use_few_shot = st.checkbox(
                "📖 Few-Shot Examples",
                value=profile.use_few_shot,
                help="Use example queries"
            )
        
        with col4:
            # Display options
            show_confidence = st.checkbox(
                "📊 Show Confidence",
                value=profile.show_confidence,
                help="Display confidence scores"
            )
            
            show_alternatives = st.checkbox(
                "🔀 Show Alternatives",
                value=profile.show_alternatives,
                help="Show alternative queries"
            )
            
            show_optimization = st.checkbox(
                "⚡ Show Optimizations",
                value=profile.show_optimization_notes,
                help="Display optimization notes"
            )
        
        # Apply all changes
        if st.button("Apply All Changes", type="primary", use_container_width=True):
            self.config_manager.update_profile(
                profile.name,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=freq_penalty,
                presence_penalty=pres_penalty,
                max_tokens=max_tokens,
                max_context_tokens=context_tokens,
                use_chain_of_thought=use_chain,
                use_self_reflection=use_reflection,
                use_few_shot=use_few_shot,
                show_confidence=show_confidence,
                show_alternatives=show_alternatives,
                show_optimization_notes=show_optimization
            )
            st.success("All parameters updated!")
            st.rerun()
    
    def _render_performance_settings(self):
        """Render performance settings tab."""
        profile = st.session_state.model_profile
        
        if not profile:
            st.info("No profile selected")
            return
        
        st.markdown("### Performance Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Timeouts")
            
            request_timeout = st.number_input(
                "Request Timeout (s)",
                min_value=1.0,
                max_value=60.0,
                value=profile.request_timeout,
                step=1.0,
                help="Maximum time for request"
            )
            
            feedback_timeout = st.number_input(
                "Feedback Timeout (s)",
                min_value=0.5,
                max_value=10.0,
                value=profile.feedback_timeout,
                step=0.5,
                help="Maximum time for feedback"
            )
            
            stream_delay = st.slider(
                "Stream Chunk Delay (s)",
                min_value=0.0,
                max_value=1.0,
                value=profile.stream_chunk_delay,
                step=0.05,
                help="Delay between stream chunks"
            )
        
        with col2:
            st.markdown("#### Caching")
            
            cache_ttl = st.number_input(
                "Cache TTL (seconds)",
                min_value=0,
                max_value=86400,
                value=profile.cache_ttl,
                step=300,
                help="Cache time-to-live"
            )
            
            cache_similar = st.checkbox(
                "Cache Similar Queries",
                value=profile.cache_similar_queries,
                help="Cache results for similar queries"
            )
            
            if cache_similar:
                similarity_threshold = st.slider(
                    "Similarity Threshold",
                    min_value=0.5,
                    max_value=1.0,
                    value=profile.similarity_threshold,
                    step=0.05,
                    help="Minimum similarity for cache hit"
                )
            else:
                similarity_threshold = profile.similarity_threshold
        
        # Optimization presets
        st.markdown("### Quick Optimization")
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            if st.button("🚀 Ultra Fast", use_container_width=True):
                self.config_manager.update_profile(
                    profile.name,
                    request_timeout=3.0,
                    feedback_timeout=0.5,
                    stream_chunk_delay=0.05,
                    thinking_depth="minimal"
                )
                st.success("Optimized for ultra-fast response!")
                st.rerun()
        
        with col4:
            if st.button("⚖️ Balanced", use_container_width=True):
                self.config_manager.update_profile(
                    profile.name,
                    request_timeout=10.0,
                    feedback_timeout=2.0,
                    stream_chunk_delay=0.1,
                    thinking_depth="standard"
                )
                st.success("Balanced settings applied!")
                st.rerun()
        
        with col5:
            if st.button("🎯 High Quality", use_container_width=True):
                self.config_manager.update_profile(
                    profile.name,
                    request_timeout=30.0,
                    feedback_timeout=5.0,
                    stream_chunk_delay=0.15,
                    thinking_depth="comprehensive"
                )
                st.success("Optimized for quality!")
                st.rerun()
        
        # Apply changes
        if st.button("Apply Performance Settings", type="primary", use_container_width=True):
            self.config_manager.update_profile(
                profile.name,
                request_timeout=request_timeout,
                feedback_timeout=feedback_timeout,
                stream_chunk_delay=stream_delay,
                cache_ttl=cache_ttl,
                cache_similar_queries=cache_similar,
                similarity_threshold=similarity_threshold
            )
            st.success("Performance settings updated!")
            st.rerun()
    
    def _render_import_export(self):
        """Render import/export tab."""
        st.markdown("### Import/Export Profiles")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Export Profile")
            
            profiles = self.config_manager.list_profiles()
            export_profile = st.selectbox(
                "Select profile to export",
                options=profiles
            )
            
            export_format = st.radio(
                "Export format",
                options=["JSON", "YAML"],
                horizontal=True
            )
            
            if st.button("Export Profile"):
                profile = self.config_manager.get_profile(export_profile)
                if profile:
                    # Create download content
                    if export_format == "JSON":
                        content = json.dumps(profile.to_dict(), indent=2)
                        file_name = f"{export_profile}.json"
                        mime = "application/json"
                    else:
                        import yaml
                        content = yaml.dump(profile.to_dict(), default_flow_style=False)
                        file_name = f"{export_profile}.yaml"
                        mime = "text/yaml"
                    
                    st.download_button(
                        label="Download Profile",
                        data=content,
                        file_name=file_name,
                        mime=mime
                    )
        
        with col2:
            st.markdown("#### Import Profile")
            
            uploaded_file = st.file_uploader(
                "Choose a profile file",
                type=["json", "yaml", "yml"]
            )
            
            if uploaded_file:
                # Parse uploaded file
                try:
                    content = uploaded_file.read().decode('utf-8')
                    
                    if uploaded_file.name.endswith('.json'):
                        profile_data = json.loads(content)
                    else:
                        import yaml
                        profile_data = yaml.safe_load(content)
                    
                    # Import profile
                    import_name = st.text_input(
                        "Profile name",
                        value=Path(uploaded_file.name).stem
                    )
                    
                    if st.button("Import Profile"):
                        # Create profile from data
                        profile = ModelProfile.from_dict(profile_data)
                        profile.name = import_name
                        
                        # Save to config manager
                        self.config_manager.profiles[import_name] = profile
                        self.config_manager.save_profile(import_name)
                        
                        st.success(f"Profile '{import_name}' imported successfully!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error importing profile: {str(e)}")
    
    def get_current_config(self) -> Dict[str, Any]:
        """
        Get current configuration for use in generation.
        
        Returns:
            Configuration dictionary
        """
        profile = st.session_state.model_profile
        mode = st.session_state.generation_mode
        
        return {
            "profile": profile,
            "mode": mode,
            "profile_name": profile.name if profile else None,
            "settings": profile.to_dict() if profile else {}
        }


def demo_config_ui():
    """Demo function for the configuration UI."""
    st.set_page_config(page_title="LLM Config Demo", layout="wide")
    
    st.title("LLM Model Configuration Demo")
    
    # Create config UI
    config_ui = ModelConfigUI()
    
    # Sidebar config
    config_ui.render_sidebar_config()
    
    # Main config panel
    config_ui.render_main_config_panel()
    
    # Show current config
    st.markdown("---")
    st.markdown("### Current Configuration")
    config = config_ui.get_current_config()
    st.json(config)


if __name__ == "__main__":
    demo_config_ui()